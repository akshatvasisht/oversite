import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../api';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { useToast } from '../context/ToastContext';

export interface Hunk {
    start_line: number;
    end_line: number;
    original_code: string;
    proposed_code: string;
}

export interface PendingSuggestion {
    suggestionId: string;
    hunks: Hunk[];
    shownAt: string;
}

interface Message {
    id: string;
    role: 'user' | 'ai' | 'system';
    content: string;
    timestamp: Date;
    hasSuggestion?: boolean;
}

interface HistoryEntry {
    role: 'user' | 'model';
    content: string;
}

interface AIChatPanelProps {
    sessionId: string | null;
    activeFileId: string | null;
    activeContent: string;
    pendingSuggestion: PendingSuggestion | null;
    onSuggestion: (suggestion: PendingSuggestion) => void;
    onResolvePending: () => void;
}

const CODE_BLOCK_RE = /```[\w]*\n?([\s\S]*?)```/;

function extractProposedCode(text: string): string | null {
    const match = CODE_BLOCK_RE.exec(text);
    return match ? match[1].trim() : null;
}

/** Split message text into alternating prose / code-block segments */
function parseSegments(text: string): { type: 'text' | 'code'; content: string }[] {
    const parts = text.split(/(```[\w]*\n?[\s\S]*?```)/g);
    return parts
        .filter((p) => p.length > 0)
        .map((p) => {
            const codeMatch = /^```[\w]*\n?([\s\S]*?)```$/.exec(p);
            if (codeMatch) return { type: 'code' as const, content: codeMatch[1] };
            return { type: 'text' as const, content: p };
        });
}

function MessageContent({ content, role }: { content: string; role: 'user' | 'ai' | 'system' }) {
    if (role !== 'ai') {
        return <pre className="chat-text">{content}</pre>;
    }
    const segments = parseSegments(content);
    return (
        <>
            {segments.map((seg, i) =>
                seg.type === 'code'
                    ? <code key={i} className="chat-code-block">{seg.content}</code>
                    : <pre key={i} className="chat-text">{seg.content}</pre>
            )}
        </>
    );
}

export default function AIChatPanel({
    sessionId,
    activeFileId,
    activeContent,
    pendingSuggestion,
    onSuggestion,
    onResolvePending,
}: AIChatPanelProps) {
    const { showToast } = useToast();
    const [messages, setMessages] = useState<Message[]>([]);
    const [history, setHistory] = useState<HistoryEntry[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const threadRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (threadRef.current) {
            threadRef.current.scrollTop = threadRef.current.scrollHeight;
        }
    }, [messages]);

    const addMessage = (role: Message['role'], content: string, extra?: Partial<Message>): string => {
        const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setMessages((prev) => [...prev, { id, role, content, timestamp: new Date(), ...extra }]);
        return id;
    };

    const send = useCallback(async () => {
        const text = input.trim();
        if (!text || loading || !sessionId) return;

        setInput('');
        setLoading(true);
        addMessage('user', text);

        if (pendingSuggestion) {
            onResolvePending();
        }

        const outgoingHistory = [...history];

        try {
            const chatRes = await api.post('/ai/chat', {
                prompt: text,
                file_id: activeFileId,
                history: outgoingHistory,
                ...(activeFileId && activeContent
                    ? { context: `File content:\n\`\`\`\n${activeContent}\n\`\`\`` }
                    : {}),
            });

            const { interaction_id, response, has_code_changes } = chatRes.data as {
                interaction_id: string;
                response: string;
                has_code_changes: boolean;
            };

            const hasSuggestion = has_code_changes && !!activeFileId;
            addMessage('ai', response, { hasSuggestion });

            setHistory((prev) => [
                ...prev,
                { role: 'user', content: text },
                { role: 'model', content: response },
            ]);

            if (hasSuggestion) {
                const proposedCode = extractProposedCode(response);
                if (proposedCode && proposedCode !== activeContent) {
                    try {
                        const sugRes = await api.post('/suggestions', {
                            interaction_id,
                            file_id: activeFileId,
                            original_content: activeContent,
                            proposed_content: proposedCode,
                        });
                        const { suggestion_id, hunks, shown_at } = sugRes.data as {
                            suggestion_id: string;
                            hunks: Hunk[];
                            shown_at: string;
                        };
                        onSuggestion({ suggestionId: suggestion_id, hunks, shownAt: shown_at });
                        addMessage('system', 'Suggestion ready — review the code above and apply as needed.');
                        showToast('AI Suggestion ready!', 'info');
                    } catch {
                        showToast('Failed to create suggestion', 'error');
                        // Suggestion creation failed silently; chat still works
                    }
                }
            }
        } catch {
            addMessage('system', 'AI service unavailable. Please try again.');
        } finally {
            setLoading(false);
        }
    }, [input, loading, sessionId, activeFileId, activeContent, history, pendingSuggestion, onSuggestion, onResolvePending]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            void send();
        }
    };

    return (
        <div className="chat-panel">
            <div className="chat-thread" ref={threadRef}>
                {messages.length === 0 && (
                    <p className="chat-empty">Ask for implementation hints, debugging help, or test-case ideas.</p>
                )}
                {messages.map((msg) => (
                    <div key={msg.id} className={`chat-message chat-message-${msg.role}`}>
                        <div className="chat-bubble">
                            <MessageContent content={msg.content} role={msg.role} />
                        </div>
                        <span className="chat-ts">
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </div>
                ))}
                {loading && (
                    <div className="chat-message chat-message-ai">
                        <div className="chat-bubble chat-loading">
                            <span className="chat-dot" />
                            <span className="chat-dot" />
                            <span className="chat-dot" />
                        </div>
                    </div>
                )}
            </div>

            {pendingSuggestion && (
                <div className="chat-suggestion-banner">
                    Suggestion pending in editor — review the code block above.
                </div>
            )}

            <div className="chat-input-area">
                <Textarea
                    rows={3}
                    placeholder="Ask AI for help... (Cmd+Enter to send)"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    className="chat-textarea"
                />
                <div className="chat-send-row">
                    <span className="chat-hint">⌘↵ to send</span>
                    <Button onClick={() => void send()} disabled={loading || !input.trim() || !sessionId} size="sm">
                        {loading ? 'Sending...' : 'Send'}
                    </Button>
                </div>
            </div>
        </div>
    );
}
