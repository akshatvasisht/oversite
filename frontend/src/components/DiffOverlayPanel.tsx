import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import type { Hunk, PendingSuggestion } from './AIChatPanel';
import { Button } from './ui/button';

interface DiffOverlayPanelProps {
    suggestion: PendingSuggestion;
    originalContent: string;
    onAllResolved: (finalContent: string) => void;
    onDismiss: () => void;
}

/**
 * Rebuild final file content by splicing accepted hunks into the original,
 * processed bottom-to-top so earlier line numbers stay valid.
 */
function applyDecisions(
    original: string,
    hunks: Hunk[],
    decisions: Record<number, 'accepted' | 'rejected'>,
): string {
    const lines = original.split('\n');
    const acceptedIndices = Object.entries(decisions)
        .filter(([, d]) => d === 'accepted')
        .map(([i]) => Number(i))
        .sort((a, b) => b - a); // descending — preserve earlier line numbers

    for (const idx of acceptedIndices) {
        const hunk = hunks[idx];
        const start = hunk.start_line - 1; // convert 1-based → 0-based
        const deleteCount = hunk.end_line - hunk.start_line + 1;
        const newLines = hunk.proposed_code.split('\n');
        if (newLines.at(-1) === '') newLines.pop(); // trim trailing empty from split
        lines.splice(start, deleteCount, ...newLines);
    }
    return lines.join('\n');
}

export default function DiffOverlayPanel({
    suggestion,
    originalContent,
    onAllResolved,
    onDismiss,
}: DiffOverlayPanelProps) {
    const [currentIdx, setCurrentIdx] = useState(0);
    const [decisions, setDecisions] = useState<Record<number, 'accepted' | 'rejected'>>({});
    const [hunkShownAt, setHunkShownAt] = useState(Date.now());
    const [deciding, setDeciding] = useState(false);

    const totalHunks = suggestion.hunks.length;
    const currentHunk = suggestion.hunks[currentIdx];
    const decidedCount = Object.keys(decisions).length;

    // Reset when a new suggestion arrives
    useEffect(() => {
        setCurrentIdx(0);
        setDecisions({});
        setHunkShownAt(Date.now());
    }, [suggestion.suggestionId]);

    // Once every hunk has a decision, compute final content and resolve
    useEffect(() => {
        if (decidedCount === totalHunks && totalHunks > 0) {
            const finalContent = applyDecisions(originalContent, suggestion.hunks, decisions);
            onAllResolved(finalContent);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [decidedCount, totalHunks]);

    const decide = useCallback(async (decision: 'accepted' | 'rejected') => {
        if (deciding || !currentHunk) return;
        setDeciding(true);

        const timeMs = Math.max(100, Math.min(300_000, Date.now() - hunkShownAt));
        const finalCode = decision === 'accepted'
            ? currentHunk.proposed_code
            : currentHunk.original_code;

        try {
            await api.post(`/suggestions/${suggestion.suggestionId}/chunks/${currentIdx}/decide`, {
                decision,
                final_code: finalCode,
                time_on_chunk_ms: timeMs,
            });
        } catch {
            // best-effort — record locally even if backend fails
        }

        setDecisions((prev) => ({ ...prev, [currentIdx]: decision }));
        setHunkShownAt(Date.now());
        setDeciding(false);
        if (currentIdx + 1 < totalHunks) {
            setCurrentIdx((prev) => prev + 1);
        }
    }, [deciding, currentIdx, currentHunk, hunkShownAt, suggestion.suggestionId, totalHunks]);

    if (!currentHunk) return null;

    return (
        <div className="diff-overlay">
            <div className="diff-overlay-header">
                <span className="diff-overlay-title">Suggested Change</span>
                <span className="diff-overlay-counter">{currentIdx + 1} / {totalHunks}</span>
                <button className="diff-dismiss-btn" onClick={onDismiss} title="Dismiss suggestion">
                    ✕
                </button>
            </div>

            <div className="diff-hunk-body">
                {currentHunk.original_code.trim() && (
                    <div className="diff-section">
                        <div className="diff-section-label diff-label-remove">− remove</div>
                        <pre className="diff-code diff-code-remove">{currentHunk.original_code}</pre>
                    </div>
                )}
                {currentHunk.proposed_code.trim() && (
                    <div className="diff-section">
                        <div className="diff-section-label diff-label-add">+ add</div>
                        <pre className="diff-code diff-code-add">{currentHunk.proposed_code}</pre>
                    </div>
                )}
            </div>

            <div className="diff-overlay-actions">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void decide('rejected')}
                    disabled={deciding}
                >
                    Reject
                </Button>
                <Button
                    size="sm"
                    onClick={() => void decide('accepted')}
                    disabled={deciding}
                >
                    {deciding ? '…' : 'Accept ✓'}
                </Button>
            </div>
        </div>
    );
}
