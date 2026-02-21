import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../api';

export interface SessionFile {
    fileId: string;
    filename: string;
    language: string;
    content: string;
    persisted: boolean;
}

interface UseSessionParams {
    routeSessionId: string;
    username: string;
    setSessionIdInContext: (id: string | null) => void;
}

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
}

const starterContent = `def solve():
    nums = [1, 2, 3]
    return sum(nums)

print(solve())
`;

const fallbackSessionId = (): string => `local-${Date.now().toString(36)}`;

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

    useEffect(() => {
        let isCancelled = false;

        const startSession = async (): Promise<void> => {
            setLoading(true);
            setError(null);

            let resolvedSessionId: string;
            try {
                const response = await api.post('/session/start', {
                    username,
                    project_name: routeSessionId,
                });
                resolvedSessionId = response.data?.session_id ?? fallbackSessionId();
            } catch {
                resolvedSessionId = fallbackSessionId();
                if (!isCancelled) {
                    setError('Using local fallback until /session/start is available.');
                }
            }

            if (isCancelled) return;

            const initialFile = createLocalFile('main.py', starterContent);
            setSessionId(resolvedSessionId);
            setSessionIdInContext(resolvedSessionId);
            setFiles([initialFile]);
            setActiveFileId(initialFile.fileId);
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
        const file = files.find((entry) => entry.fileId === targetFileId);
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
    }, [files]);

    const selectFile = useCallback(async (fileId: string): Promise<void> => {
        const resolvedFileId = await persistFileIfNeeded(fileId);
        setActiveFileId(resolvedFileId);
    }, [persistFileIfNeeded]);

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
    };
};
