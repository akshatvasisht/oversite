import Editor from '@monaco-editor/react';

interface MonacoEditorWrapperProps {
    fileId?: string;
    content: string;
    language?: string;
    onChange?: (value: string | undefined) => void;
}

const MonacoEditorWrapper: React.FC<MonacoEditorWrapperProps> = ({ content, language = 'python', onChange }) => {
    return (
        <div style={{ height: '500px', width: '800px', border: '1px solid #ccc' }}>
            <Editor
                height="100%"
                defaultLanguage={language}
                value={content}
                onChange={onChange}
                options={{
                    minimap: { enabled: false }
                }}
            />
        </div>
    );
};

export default MonacoEditorWrapper;
