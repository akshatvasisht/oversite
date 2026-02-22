import { useState } from 'react';
import type { SessionFile } from '../hooks/useSession';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface FileExplorerProps {
    files: SessionFile[];
    activeFileId: string | null;
    onSelectFile: (fileId: string) => Promise<void>;
    onCreateFile: (filename: string) => Promise<void>;
}

function fileIcon(filename: string): string {
    if (filename.endsWith('.py')) return '🐍';
    if (filename.endsWith('.js') || filename.endsWith('.ts')) return '📜';
    if (filename.endsWith('.json')) return '{}';
    if (filename.endsWith('.md')) return '📝';
    if (filename.endsWith('.sql')) return '🗄';
    return '📄';
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
        <aside className="file-explorer">
            <div className="file-explorer-title">Explorer</div>
            <div className="file-create-row">
                <Input
                    type="text"
                    value={draftFilename}
                    onChange={(event) => setDraftFilename(event.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') void handleCreate(); }}
                    placeholder="new_file.py"
                    className="file-create-input"
                />
                <Button size="sm" variant="secondary" onClick={() => { void handleCreate(); }}>
                    +
                </Button>
            </div>
            <div className="file-list">
                {files.map((file) => (
                    <button
                        key={file.fileId}
                        onClick={() => { void onSelectFile(file.fileId); }}
                        className={`file-item ${file.fileId === activeFileId ? 'active' : ''}`}
                    >
                        <span style={{ marginRight: 6, fontSize: 12 }}>{fileIcon(file.filename)}</span>
                        {file.filename}
                    </button>
                ))}
            </div>
        </aside>
    );
};

export default FileExplorer;
