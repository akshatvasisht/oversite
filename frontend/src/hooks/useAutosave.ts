import { useEffect, useRef, useState } from 'react';

type SaveTrigger = 'debounce' | 'file_switch';
type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface UseAutosaveParams {
    fileId: string | null;
    content: string;
    onSave: (fileId: string, content: string, trigger: SaveTrigger) => Promise<void>;
    delayMs?: number;
}

interface UseAutosaveResult {
    status: AutosaveStatus;
}

export const useAutosave = ({
    fileId,
    content,
    onSave,
    delayMs = 2000,
}: UseAutosaveParams): UseAutosaveResult => {
    const [status, setStatus] = useState<AutosaveStatus>('idle');
    const saveSequenceRef = useRef(0);

    useEffect(() => {
        if (!fileId) {
            return;
        }

        const sequence = ++saveSequenceRef.current;
        const timer = window.setTimeout(async () => {
            try {
                setStatus('saving');
                await onSave(fileId, content, 'debounce');
                if (saveSequenceRef.current === sequence) {
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
    }, [content, delayMs, fileId, onSave]);

    return { status: fileId ? status : 'idle' };
};
