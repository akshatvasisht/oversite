import React, { useState, useMemo } from 'react';
import type { SessionFile } from '../hooks/useSession';
import { Button } from './ui/button';
import { Input } from './ui/input';

/**
 * Properties for the FileExplorer component.
 */
interface FileExplorerProps {
    files: SessionFile[];
    activeFileId: string | null;
    onSelectFile: (fileId: string) => Promise<void>;
    onCreateFile: (filename: string) => Promise<void>;
}

/**
 * Node within the virtual file system tree used for hierarchical display.
 */
interface TreeNode {
    name: string;
    path: string;
    fileId?: string;
    children?: Record<string, TreeNode>;
    isFolder: boolean;
}

/**
 * Constructs a recursive tree structure from a flat list of assessment files.
 */
const buildFileTree = (files: SessionFile[]): TreeNode => {
    const root: TreeNode = { name: 'root', path: '', children: {}, isFolder: true };

    files.forEach((file) => {
        const parts = file.filename.split('/');
        let current = root;

        parts.forEach((part, index) => {
            if (!current.children) current.children = {};

            if (!current.children[part]) {
                const isFolder = index < parts.length - 1;
                current.children[part] = {
                    name: part,
                    path: parts.slice(0, index + 1).join('/'),
                    isFolder,
                    children: isFolder ? {} : undefined,
                    fileId: isFolder ? undefined : file.fileId,
                };
            }
            current = current.children[part];
        });
    });

    return root;
};

/**
 * Properties for individual file or folder nodes in the explorer tree.
 */
interface FileItemProps {
    node: TreeNode;
    level: number;
    activeFileId: string | null;
    onSelectFile: (fileId: string) => Promise<void>;
}

/**
 * Renders a single node in the file explorer tree, handling recursive folder expansion.
 */
const FileItem: React.FC<FileItemProps> = ({ node, level, activeFileId, onSelectFile }) => {
    const [isOpen, setIsOpen] = useState(true);

    if (!node.isFolder) {
        return (
            <button
                onClick={() => node.fileId && void onSelectFile(node.fileId)}
                className={`file-item ${node.fileId === activeFileId ? 'active' : ''}`}
                style={{ paddingLeft: level * 12 + 16 }}
            >
                {node.name}
            </button>
        );
    }

    const children = Object.values(node.children || {}).sort((a, b) => {
        if (a.isFolder && !b.isFolder) return -1;
        if (!a.isFolder && b.isFolder) return 1;
        return a.name.localeCompare(b.name);
    });

    return (
        <div className="folder-item">
            <button
                className="folder-toggle"
                onClick={() => setIsOpen(!isOpen)}
                style={{ paddingLeft: level * 12 + 12 }}
            >
                <span className={`folder-carat ${isOpen ? 'open' : ''}`}>›</span>
                {node.name}
            </button>
            {isOpen && (
                <div className="folder-children">
                    {children.map((child) => (
                        <FileItem
                            key={child.path}
                            node={child}
                            level={level + 1}
                            activeFileId={activeFileId}
                            onSelectFile={onSelectFile}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

/**
 * Navigation sidebar for managing and selecting workspace files with directory support.
 */
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

    const tree = useMemo(() => buildFileTree(files), [files]);
    const rootChildren = useMemo(() => {
        return Object.values(tree.children || {}).sort((a, b) => {
            if (a.isFolder && !b.isFolder) return -1;
            if (!a.isFolder && b.isFolder) return 1;
            return a.name.localeCompare(b.name);
        });
    }, [tree]);

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
                {rootChildren.map((node) => (
                    <FileItem
                        key={node.path}
                        node={node}
                        level={0}
                        activeFileId={activeFileId}
                        onSelectFile={onSelectFile}
                    />
                ))}
            </div>
        </aside>
    );
};

export default FileExplorer;
