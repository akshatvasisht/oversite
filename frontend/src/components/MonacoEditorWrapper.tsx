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
    content,
    language = 'python',
    onChange,
    onMount
}) => {
    return (
        <div style={{ height: '500px', width: '800px', border: '1px solid #ccc' }}>
            <Editor
                height="100%"
                defaultLanguage={language}
                value={content}
                onChange={onChange}
                onMount={onMount}
                options={{
                    minimap: { enabled: false }
                }}
            />
        </div>
    );
};

export default MonacoEditorWrapper;
