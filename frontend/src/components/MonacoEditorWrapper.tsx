import Editor from '@monaco-editor/react';
import type { OnMount } from '@monaco-editor/react';

interface MonacoEditorWrapperProps {
    fileId?: string;
    content: string;
    language?: string;
    onChange?: (value: string | undefined) => void;
    onMount?: OnMount;
}

const MonacoEditorWrapper: React.FC<MonacoEditorWrapperProps> = ({
    fileId,
    content,
    language = 'python',
    onChange,
    onMount
}) => {
    return (
        <div className="editor-shell">
            <Editor
                path={fileId}
                height="100%"
                language={language}
                value={content}
                onChange={onChange}
                onMount={onMount}
                options={{
                    lineNumbers: 'on',
                    minimap: { enabled: false }
                }}
            />
        </div>
    );
};

export default MonacoEditorWrapper;
