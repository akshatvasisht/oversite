import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import * as monaco from 'monaco-editor';
import api from '../api';
import { useToast } from '../context/ToastContext';
import type { PendingSuggestion, Hunk } from './AIChatPanel';

interface DiffOverlayProps {
    editor: monaco.editor.IStandaloneCodeEditor | null;
    monacoApi: typeof monaco | null;
    pendingSuggestion: PendingSuggestion | null;
    onResolvePending: () => void;
    onFileUpdate: (content: string) => void;
    activeFileId: string | null;
    sessionId: string | null;
}

class HunkContentWidget implements monaco.editor.IContentWidget {
    private id: string;
    public domNode: HTMLElement;
    public lineNumber: number;

    constructor(index: number, lineNumber: number) {
        this.id = `hunk-widget-${index}`;
        this.domNode = document.createElement('div');
        this.domNode.style.zIndex = '50';
        this.lineNumber = lineNumber;
    }

    getId() { return this.id; }
    getDomNode() { return this.domNode; }
    getPosition() {
        return {
            position: { lineNumber: this.lineNumber, column: 1 },
            preference: [monaco.editor.ContentWidgetPositionPreference.ABOVE]
        };
    }
}

export function DiffOverlay({
    editor,
    monacoApi,
    pendingSuggestion,
    onResolvePending,
    onFileUpdate,
}: DiffOverlayProps) {
    const { showToast } = useToast();
    const [portals, setPortals] = useState<React.ReactPortal[]>([]);
    const decorationsCollection = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);
    const widgetsRef = useRef<Map<number, HunkContentWidget>>(new Map());
    const decisionsRef = useRef<Map<number, string>>(new Map()); // chunkIndex -> decision

    // Setup / Teardown
    useEffect(() => {
        if (!editor || !monacoApi) return;

        const cleanup = () => {
            if (decorationsCollection.current) {
                decorationsCollection.current.clear();
                decorationsCollection.current = null;
            }
            widgetsRef.current.forEach(w => editor.removeContentWidget(w));
            widgetsRef.current.clear();
            setPortals([]);
            decisionsRef.current.clear();
        };

        if (!pendingSuggestion) {
            cleanup();
            return;
        }

        cleanup();

        const newDecorations: monaco.editor.IModelDeltaDecoration[] = [];
        const newPortals: React.ReactPortal[] = [];

        pendingSuggestion.hunks.forEach((hunk, index) => {
            // Add background decoration
            // If start_line and end_line are the same or valid range
            newDecorations.push({
                range: new monacoApi.Range(hunk.start_line, 1, hunk.end_line, 1),
                options: {
                    isWholeLine: true,
                    className: 'diff-decoration-modified',
                    linesDecorationsClassName: 'diff-decoration-margin',
                }
            });

            // Add widget
            const widget = new HunkContentWidget(index, hunk.start_line);
            editor.addContentWidget(widget);
            widgetsRef.current.set(index, widget);

            // Create portal
            const portal = createPortal(
                <HunkAction
                    hunk={hunk}
                    chunkIndex={index}
                    suggestionId={pendingSuggestion.suggestionId}
                    shownAt={pendingSuggestion.shownAt}
                    onDecide={(decision, finalCode) => handleDecide(index, decision, finalCode, pendingSuggestion.suggestionId)}
                />,
                widget.domNode
            );
            newPortals.push(portal);
        });

        decorationsCollection.current = editor.createDecorationsCollection(newDecorations);

        setPortals(newPortals);

        return cleanup;
    }, [editor, monacoApi, pendingSuggestion]);

    const handleDecide = async (chunkIndex: number, decision: 'accepted' | 'rejected' | 'modified', finalCode: string, suggestionId: string) => {
        if (!editor || !monacoApi || !pendingSuggestion) return;

        // Send to backend
        const timeMs = 2500; // Mock derived time or calculated via shownAt
        try {
            await api.post(`/suggestions/${suggestionId}/chunks/${chunkIndex}/decide`, {
                decision,
                final_code: finalCode,
                time_on_chunk_ms: timeMs
            });
            showToast(`Hunk ${decision}`, decision === 'accepted' ? 'success' : 'info');
        } catch (err) {
            console.error("Decision failed", err);
            showToast("Failed to save decision", "error");
        }

        // Apply text if accepted or modified
        if (decision === 'accepted' || decision === 'modified') {
            const model = editor.getModel();
            if (model && decorationsCollection.current) {
                const ranges = decorationsCollection.current.getRanges();
                // Since decorations Collection maintains order, ranges[chunkIndex] is this hunk's current shifted range
                const currentRange = ranges[chunkIndex];
                if (currentRange) {
                    // We do a pushEditOperations to allow undo and shift decorations
                    model.pushEditOperations(
                        [],
                        [{
                            range: new monacoApi.Range(currentRange.startLineNumber, 1, currentRange.endLineNumber, model.getLineMaxColumn(currentRange.endLineNumber)),
                            text: finalCode + (finalCode.endsWith('\n') ? '' : '\n') // assure trailing newline
                        }],
                        () => null
                    );
                    onFileUpdate(model.getValue());
                }
            }
        }

        // Hide the widget
        const widget = widgetsRef.current.get(chunkIndex);
        if (widget) {
            editor.removeContentWidget(widget);
        }
        decisionsRef.current.set(chunkIndex, decision);

        // Remove just this portal
        // we can keep portals state updated or just let it unmount by filtering
        setPortals(prev => {
            // We shouldn't blindly filter by index because matching portal to index is tricky.
            // But since we built them in order, we could just return null for this index in the render.
            // Actually, React doesn't mind if we leave the portal but clear the DOM node, but it's cleaner to remove it.
            // For simplicity we will tell the component to hide itself.
            return prev;
        });

        // Check if all chunks decided
        if (decisionsRef.current.size === pendingSuggestion.hunks.length) {
            onResolvePending(); // cleans up everything
        } else {
            // Update widget positions because lines might have shifted
            if (decorationsCollection.current) {
                const newRanges = decorationsCollection.current.getRanges();
                widgetsRef.current.forEach((w, idx) => {
                    if (!decisionsRef.current.has(idx) && newRanges[idx]) {
                        w.lineNumber = newRanges[idx].startLineNumber;
                        editor.layoutContentWidget(w);
                    }
                });
            }
        }
    };

    return <>{portals}</>;
}

interface HunkActionProps {
    hunk: Hunk;
    chunkIndex: number;
    suggestionId: string;
    shownAt: string;
    onDecide: (decision: 'accepted' | 'rejected' | 'modified', finalCode: string) => Promise<void>;
}

function HunkAction({ hunk, onDecide }: HunkActionProps) {
    const [loading, setLoading] = useState(false);
    const [hidden, setHidden] = useState(false);

    const act = async (decision: 'accepted' | 'rejected', code: string) => {
        setLoading(true);
        await onDecide(decision, code);
        setHidden(true);
    };

    if (hidden) return null;

    return (
        <div className="hunk-action-widget" style={{
            display: 'flex', gap: 8, padding: '4px 8px',
            background: 'var(--bg-surface)', border: '1px solid var(--border-color)',
            borderRadius: 6, boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
            <button
                disabled={loading}
                onClick={() => void act('accepted', hunk.proposed_code)}
                style={{ background: 'var(--success-color)', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 10px', fontSize: 12, cursor: 'pointer' }}
            >
                Accept
            </button>
            <button
                disabled={loading}
                onClick={() => void act('rejected', hunk.original_code)}
                style={{ background: 'var(--danger-color)', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 10px', fontSize: 12, cursor: 'pointer' }}
            >
                Reject
            </button>
        </div>
    );
}
