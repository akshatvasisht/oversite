import { useEffect, useRef, useState } from 'react';

/**
 * Identified reason for a save event (either debounce timeout or active file change).
 */
type SaveTrigger = 'debounce' | 'file_switch';

/**
 * Operational status of the automated saving mechanism.
 */
type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

/**
 * Parameters for configuring the useAutosave hook.
 */
interface UseAutosaveParams {
    fileId: string | null;
    content: string;
    onSave: (fileId: string, content: string, trigger: SaveTrigger) => Promise<void>;
    delayMs?: number;
}

/**
 * Current status of the autosave background task.
 */
interface UseAutosaveResult {
    status: AutosaveStatus;
}

/**
 * Custom hook to manage debounced autosave functionality for editor content.
 * 
 * Tracks a sequence of edits and triggers the provided onSave callback after 
 * the specified delay. Ensures that only the latest content is persisted and 
 * handles saving on component unmount.
 * 
 * @param params Configuration for the autosave behavior.
 * @returns The current status of the autosave operation ('idle', 'saving', 'saved', 'error').
 */
export const useAutosave = ({
    fileId,
    content,
    onSave,
    delayMs = 2000,
}: UseAutosaveParams): UseAutosaveResult => {
    const [status, setStatus] = useState<AutosaveStatus>('idle');
    const contentRef = useRef(content);
    const onSaveRef = useRef(onSave);
    const lastSavedContentRef = useRef(content);
    const saveSequenceRef = useRef(0);

    // Keep refs in sync with props to allow the effect to use latest values without re-running
    useEffect(() => {
        contentRef.current = content;
        onSaveRef.current = onSave;
    }, [content, onSave]);

    useEffect(() => {
        if (!fileId) {
            return;
        }

        // If content matches what we last saved (e.g. on file switch or redundant update), skip
        if (content === lastSavedContentRef.current) {
            return;
        }

        const sequence = ++saveSequenceRef.current;
        const timer = window.setTimeout(async () => {
            try {
                setStatus('saving');
                await onSaveRef.current(fileId, contentRef.current, 'debounce');
                if (saveSequenceRef.current === sequence) {
                    lastSavedContentRef.current = contentRef.current;
                    setStatus('saved');
                }
            } catch {
                if (saveSequenceRef.current === sequence) {
                    setStatus('error');
                }
            }
        }, delayMs);

        return () => {
            window.clearTimeout(timer);
        };
    }, [fileId, delayMs, content]);

    // Final save on unmount only if content has changed since last save
    useEffect(() => {
        return () => {
            if (fileId && contentRef.current !== lastSavedContentRef.current) {
                void onSaveRef.current(fileId, contentRef.current, 'debounce');
            }
        };
    }, [fileId]);

    return { status: fileId ? status : 'idle' };
};
