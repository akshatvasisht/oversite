import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import type { OnMount } from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import { DiffOverlay } from './DiffOverlay';
import type { PendingSuggestion } from './AIChatPanel';

interface MonacoEditorWrapperProps {
    fileId?: string;
    content: string;
    language?: string;
    onChange?: (value: string | undefined) => void;
    onMount?: OnMount;
    pendingSuggestion?: PendingSuggestion | null;
    onResolvePending?: () => void;
    sessionId?: string | null;
}

/**
 * React wrapper for the Monaco Editor with telemetry and diff overlay support.
 */
const MonacoEditorWrapper: React.FC<MonacoEditorWrapperProps> = ({
    fileId,
    content,
    language = 'python',
    onChange,
    onMount,
    pendingSuggestion = null,
    onResolvePending,
    sessionId
}) => {
    const [editorRef, setEditorRef] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
    const [monacoApi, setMonacoApi] = useState<typeof monaco | null>(null);

    const handleMount: OnMount = (editor, monacoInstance) => {
        setEditorRef(editor);
        setMonacoApi(monacoInstance);
        if (onMount) {
            onMount(editor, monacoInstance);
        }
    };

    return (
        <div className="editor-shell">
            <Editor
                path={fileId}
                height="100%"
                language={language}
                value={content}
                onChange={onChange}
                onMount={handleMount}
                theme="vs-dark"
                options={{
                    lineNumbers: 'on',
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: "'JetBrains Mono', Consolas, 'Courier New', monospace",
                    fontLigatures: false,
                    scrollBeyondLastLine: false,
                    padding: { top: 12, bottom: 12 },
                }}
            />
            {onResolvePending && (
                <DiffOverlay
                    editor={editorRef}
                    monacoApi={monacoApi}
                    pendingSuggestion={pendingSuggestion}
                    onResolvePending={onResolvePending}
                    onFileUpdate={(val) => { if (onChange) onChange(val); }}
                    activeFileId={fileId || null}
                    sessionId={sessionId || null}
                />
            )}
        </div>
    );
};

export default MonacoEditorWrapper;
