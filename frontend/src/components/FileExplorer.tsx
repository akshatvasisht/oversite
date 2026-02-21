import { useState } from 'react';
import type { SessionFile } from '../hooks/useSession';

interface FileExplorerProps {
    files: SessionFile[];
    activeFileId: string | null;
    onSelectFile: (fileId: string) => Promise<void>;
    onCreateFile: (filename: string) => Promise<void>;
}

const FileExplorer: React.FC<FileExplorerProps> = ({
    files,
    activeFileId,
    onSelectFile,
    onCreateFile,
}) => {
    const [draftFilename, setDraftFilename] = useState('');

    const handleCreate = async (): Promise<void> => {
        const filename = draftFilename.trim();
        if (!filename) return;
        await onCreateFile(filename);
        setDraftFilename('');
    };

    return (
        <aside
            style={{
                width: '240px',
                border: '1px solid #d4d4d8',
                borderRadius: '8px',
                padding: '12px',
                background: '#fafafa',
            }}
        >
            <h3 style={{ margin: '0 0 10px' }}>Files</h3>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                    type="text"
                    value={draftFilename}
                    onChange={(event) => setDraftFilename(event.target.value)}
                    placeholder="utils.py"
                    style={{ flex: 1, padding: '6px 8px' }}
                />
                <button type="button" onClick={() => { void handleCreate(); }}>
                    Add
                </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {files.map((file) => (
                    <button
                        key={file.fileId}
                        type="button"
                        onClick={() => { void onSelectFile(file.fileId); }}
                        style={{
                            textAlign: 'left',
                            borderRadius: '6px',
                            padding: '8px',
                            cursor: 'pointer',
                            border: file.fileId === activeFileId ? '1px solid #1d4ed8' : '1px solid #e4e4e7',
                            background: file.fileId === activeFileId ? '#eff6ff' : '#ffffff',
                        }}
                    >
                        {file.filename}
                    </button>
                ))}
            </div>
        </aside>
    );
};

export default FileExplorer;

