import React, { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import * as monaco from 'monaco-editor';
import api from '../api';
import { useToast } from '../context/ToastContext';
import type { PendingSuggestion, Hunk } from './AIChatPanel';

/**
 * Props for the DiffOverlay component.
 */
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

/**
 * Monaco Editor overlay for reviewing and applying AI-generated code changes.
 * 
 * Uses Monaco ContentWidgets and EditorDecorations to render inline hunks 
 * with Accept/Reject controls.
 */
export function DiffOverlay({
    editor,
    monacoApi,
    pendingSuggestion,
    onResolvePending,
    onFileUpdate,
}: DiffOverlayProps) {
    const { showToast } = useToast();
    const [widgetNodes, setWidgetNodes] = useState<Map<number, HTMLElement>>(new Map());
    const decorationsCollection = useRef<monaco.editor.IEditorDecorationsCollection | null>(null);
    const widgetsRef = useRef<Map<number, HunkContentWidget>>(new Map());
    const decisionsRef = useRef<Map<number, string>>(new Map()); // chunkIndex -> decision

    const handleDecide = React.useCallback(async (chunkIndex: number, decision: 'accepted' | 'rejected' | 'modified', finalCode: string, suggestionId: string) => {
        if (!editor || !monacoApi || !pendingSuggestion) return;

        const timeMs = 2500;
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

        if (decision === 'accepted' || decision === 'modified') {
            const model = editor.getModel();
            if (model && decorationsCollection.current) {
                const ranges = decorationsCollection.current.getRanges();
                const currentRange = ranges[chunkIndex];
                if (currentRange) {
                    model.pushEditOperations(
                        [],
                        [{
                            range: new monacoApi.Range(currentRange.startLineNumber, 1, currentRange.endLineNumber, model.getLineMaxColumn(currentRange.endLineNumber)),
                            text: finalCode + (finalCode.endsWith('\n') ? '' : '\n')
                        }],
                        () => null
                    );
                    onFileUpdate(model.getValue());
                }
            }
        }

        const widget = widgetsRef.current.get(chunkIndex);
        if (widget) {
            editor.removeContentWidget(widget);
        }
        decisionsRef.current.set(chunkIndex, decision);
        // Remove from state to hide portal
        queueMicrotask(() => {
            setWidgetNodes(prev => {
                const next = new Map(prev);
                next.delete(chunkIndex);
                return next;
            });
        });

        if (decisionsRef.current.size === pendingSuggestion.hunks.length) {
            onResolvePending();
        } else {
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
    }, [editor, monacoApi, pendingSuggestion, showToast, onFileUpdate, onResolvePending]);

    // Setup / Teardown
    useLayoutEffect(() => {
        if (!editor || !monacoApi) return;

        const cleanup = () => {
            if (decorationsCollection.current) {
                decorationsCollection.current.clear();
                decorationsCollection.current = null;
            }
            widgetsRef.current.forEach(w => editor.removeContentWidget(w));
            widgetsRef.current.clear();
            setWidgetNodes(new Map());
            decisionsRef.current.clear();
        };

        if (!pendingSuggestion) {
            cleanup();
            return;
        }

        cleanup();

        const newDecorations: monaco.editor.IModelDeltaDecoration[] = [];
        const newNodes = new Map<number, HTMLElement>();

        pendingSuggestion.hunks.forEach((hunk, index) => {
            newDecorations.push({
                range: new monacoApi.Range(hunk.start_line, 1, hunk.end_line, 1),
                options: {
                    isWholeLine: true,
                    className: 'diff-decoration-modified',
                    linesDecorationsClassName: 'diff-decoration-margin',
                }
            });

            const widget = new HunkContentWidget(index, hunk.start_line);
            editor.addContentWidget(widget);
            widgetsRef.current.set(index, widget);
            newNodes.set(index, widget.domNode);
        });

        decorationsCollection.current = editor.createDecorationsCollection(newDecorations);
        queueMicrotask(() => setWidgetNodes(newNodes));

        return cleanup;
    }, [editor, monacoApi, pendingSuggestion]);

    if (!pendingSuggestion) return null;

    return (
        <>
            {pendingSuggestion.hunks.map((hunk, index) => {
                const node = widgetNodes.get(index);
                if (!node) return null;

                return createPortal(
                    <HunkAction
                        hunk={hunk}
                        chunkIndex={index}
                        suggestionId={pendingSuggestion.suggestionId}
                        shownAt={pendingSuggestion.shownAt}
                        onDecide={(d, c) => handleDecide(index, d, c, pendingSuggestion.suggestionId)}
                    />,
                    node
                );
            })}
        </>
    );
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
