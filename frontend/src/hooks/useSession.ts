import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../api';

/**
 * Metadata for a file persisted within an assessment session.
 */
export interface SessionFile {
    fileId: string;
    filename: string;
    language: string;
    content: string;
    persisted: boolean;
}

/**
 * Parameters required to initialize the useSession hook.
 */
interface UseSessionParams {
    routeSessionId: string;
    username: string;
    setSessionIdInContext: (id: string | null) => void;
}

/**
 * Return type for the useSession hook containing assessment state and handlers.
 */
interface UseSessionResult {
    loading: boolean;
    error: string | null;
    sessionId: string | null;
    files: SessionFile[];
    activeFileId: string | null;
    activeFile: SessionFile | null;
    activeContent: string;
    selectFile: (fileId: string) => Promise<void>;
    createFile: (filename: string) => Promise<void>;
    updateActiveContent: (content: string) => void;
    saveEditorEvent: (
        fileId: string,
        content: string,
        trigger: 'debounce' | 'file_switch',
    ) => Promise<void>;
    startedAt: string | null;
    initialElapsedSeconds: number;
    description: string;
    title: string;
    difficulty: string;
    duration: string;
}

// Baseline assessment configuration is now dynamically loaded from the backend
// during session initialization. This allows for filesystem-based problem discovery.

const fallbackSessionId = (): string => `local-${Date.now().toString(36)}`;

/**
 * Detects the appropriate programming language based on file extension.
 */
const inferLanguage = (filename: string): string => {
    if (filename.endsWith('.py')) return 'python';
    if (filename.endsWith('.ts') || filename.endsWith('.tsx')) return 'typescript';
    if (filename.endsWith('.js') || filename.endsWith('.jsx')) return 'javascript';
    if (filename.endsWith('.json')) return 'json';
    return 'plaintext';
};

const createLocalFile = (filename: string, content: string): SessionFile => ({
    fileId: `local-${filename.toLowerCase().replace(/[^a-z0-9._-]/g, '-')}-${Date.now().toString(36)}`,
    filename,
    language: inferLanguage(filename),
    content,
    persisted: false,
});

/**
 * Orchestrates all session-level state, including file management and API synchronization.
 * 
 * Handles the initialization of assessment environments, rehydration of existing 
 * sessions, and persistence of editor events for the behavioral telemetry pipeline.
 * 
 * @param params Configuration for the session initialization.
 * @returns An object containing session state and interaction handlers.
 */
export const useSession = ({
    routeSessionId,
    username,
    setSessionIdInContext,
}: UseSessionParams): UseSessionResult => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [files, setFiles] = useState<SessionFile[]>([]);
    const [activeFileId, setActiveFileId] = useState<string | null>(null);
    const filesRef = useRef<SessionFile[]>([]);
    const lastSavedContentRef = useRef<Record<string, string>>({});

    useEffect(() => {
        filesRef.current = files;
    }, [files]);

    const [startedAt, setStartedAt] = useState<string | null>(null);
    const [initialElapsedSeconds, setInitialElapsedSeconds] = useState(0);
    const [description, setDescription] = useState('');
    const [title, setTitle] = useState('');
    const [difficulty, setDifficulty] = useState('');
    const [duration, setDuration] = useState('');

    useEffect(() => {
        let isCancelled = false;

        const startSession = async (): Promise<void> => {
            setLoading(true);
            setError(null);

            let resolvedSessionId: string;
            let fetchedFiles: SessionFile[] | null = null;
            let fetchedStartedAt: string | null = null;
            let fetchedElapsed = 0;
            let fetchedDescription = '';
            let fetchedTitle = '';
            let fetchedDifficulty = '';
            let fetchedDuration = '';
            try {
                const response = await api.post('/session/start', {
                    username,
                    project_name: routeSessionId,
                });
                resolvedSessionId = response.data?.session_id ?? fallbackSessionId();
                if (response.data?.files) {
                    fetchedFiles = response.data.files;
                }
                if (response.data?.started_at) {
                    fetchedStartedAt = response.data.started_at;
                }
                if (typeof response.data?.elapsed_seconds === 'number') {
                    fetchedElapsed = response.data.elapsed_seconds;
                }
                if (response.data?.description) {
                    fetchedDescription = response.data.description;
                }
                if (response.data?.title) {
                    fetchedTitle = response.data.title;
                }
                if (response.data?.difficulty) {
                    fetchedDifficulty = response.data.difficulty;
                }
                if (response.data?.duration) {
                    fetchedDuration = response.data.duration;
                }
            } catch {
                resolvedSessionId = fallbackSessionId();
                if (!isCancelled) {
                    setError('Using local fallback until /session/start is available.');
                }
            }

            if (isCancelled) return;

            // Use the files provided by the backend, or fallback if none
            const starterFiles: SessionFile[] = fetchedFiles ?? [];

            setSessionId(resolvedSessionId);
            setSessionIdInContext(resolvedSessionId);
            setFiles(starterFiles);
            setStartedAt(fetchedStartedAt);
            setInitialElapsedSeconds(fetchedElapsed);
            setDescription(fetchedDescription);
            setTitle(fetchedTitle);
            setDifficulty(fetchedDifficulty);
            setDuration(fetchedDuration);

            // Default to discount.py if present, else first file
            const initialActive = starterFiles.find(f => f.filename === 'discount.py') ?? starterFiles[0];
            setActiveFileId(initialActive?.fileId ?? null);
            setLoading(false);
        };

        void startSession();

        return () => {
            isCancelled = true;
        };
    }, [routeSessionId, setSessionIdInContext, username]);

    const activeFile = useMemo(
        () => files.find((file) => file.fileId === activeFileId) ?? null,
        [files, activeFileId],
    );

    const activeContent = activeFile?.content ?? '';

    const persistFileIfNeeded = useCallback(async (targetFileId: string): Promise<string> => {
        const file = filesRef.current.find((entry) => entry.fileId === targetFileId);
        if (!file || file.persisted) return targetFileId;

        try {
            const response = await api.post('/files', {
                filename: file.filename,
                initial_content: file.content,
            });
            const persistedId = response.data?.file_id as string | undefined;
            if (!persistedId) return targetFileId;

            setFiles((current) =>
                current.map((entry) => (
                    entry.fileId === targetFileId
                        ? { ...entry, fileId: persistedId, persisted: true }
                        : entry
                )),
            );
            setActiveFileId((current) => (current === targetFileId ? persistedId : current));
            return persistedId;
        } catch {
            // Work in local mode while endpoint is unavailable.
            return targetFileId;
        }
    }, []);

    const saveEditorEvent = useCallback(async (
        fileId: string,
        content: string,
        trigger: 'debounce' | 'file_switch',
    ): Promise<void> => {
        if (!sessionId) return;

        const lastSaved = lastSavedContentRef.current[fileId];
        if (lastSaved === content) {
            return;
        }

        const resolvedFileId = await persistFileIfNeeded(fileId);
        if (lastSavedContentRef.current[resolvedFileId] === content) {
            return;
        }

        try {
            await api.post('/events/editor', {
                file_id: resolvedFileId,
                content,
                trigger,
                suggestion_id: null,
                cursor_line: 1,
                cursor_col: 1,
            });
            lastSavedContentRef.current = {
                ...lastSavedContentRef.current,
                [fileId]: content,
                [resolvedFileId]: content,
            };
        } catch {
            // Keep local editing available while backend endpoint is unavailable.
        }
    }, [persistFileIfNeeded, sessionId]);

    const selectFile = useCallback(async (fileId: string): Promise<void> => {
        const previousFileId = activeFileId;
        if (previousFileId && previousFileId !== fileId) {
            const previousFile = filesRef.current.find((file) => file.fileId === previousFileId);
            if (previousFile) {
                await saveEditorEvent(previousFile.fileId, previousFile.content, 'file_switch');
            }
        }

        const resolvedFileId = await persistFileIfNeeded(fileId);
        setActiveFileId(resolvedFileId);
    }, [activeFileId, persistFileIfNeeded, saveEditorEvent]);

    const createFile = useCallback(async (filename: string): Promise<void> => {
        if (files.some((file) => file.filename === filename)) {
            return;
        }
        const file = createLocalFile(filename, '');
        setFiles((current) => [...current, file]);
        setActiveFileId(file.fileId);
        const resolvedFileId = await persistFileIfNeeded(file.fileId);
        setActiveFileId(resolvedFileId);
    }, [files, persistFileIfNeeded]);

    const updateActiveContent = useCallback((content: string): void => {
        setFiles((current) =>
            current.map((file) => (file.fileId === activeFileId ? { ...file, content } : file)),
        );
    }, [activeFileId]);

    return {
        loading,
        error,
        sessionId,
        files,
        activeFileId,
        activeFile,
        activeContent,
        selectFile,
        createFile,
        updateActiveContent,
        saveEditorEvent,
        startedAt,
        initialElapsedSeconds,
        description,
        title,
        difficulty,
        duration,
    };
};
