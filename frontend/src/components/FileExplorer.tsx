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
            <h3 className="file-explorer-title">Files</h3>
            <div className="file-create-row">
                <Input
                    type="text"
                    value={draftFilename}
                    onChange={(event) => setDraftFilename(event.target.value)}
                    placeholder="utils.py"
                    className="file-create-input"
                />
                <Button size="sm" variant="secondary" onClick={() => { void handleCreate(); }} className="file-create-button">
                    Add
                </Button>
            </div>
            <div className="file-list">
                {files.map((file) => (
                    <Button
                        key={file.fileId}
                        variant="ghost"
                        size="sm"
                        onClick={() => { void onSelectFile(file.fileId); }}
                        className={`file-item ${file.fileId === activeFileId ? 'active' : ''}`}
                    >
                        {file.filename}
                    </Button>
                ))}
            </div>
        </aside>
    );
};

export default FileExplorer;

