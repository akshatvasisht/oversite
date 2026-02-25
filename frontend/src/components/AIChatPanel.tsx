import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import api from '../api';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { useToast } from '../context/ToastContext';

/**
 * Represents a specific block of code changes within a suggestion.
 */
export interface Hunk {
    start_line: number;
    end_line: number;
    original_code: string;
    proposed_code: string;
}

/**
 * Interface for a code modification suggestion pending candidate review.
 */
export interface PendingSuggestion {
    suggestionId: string;
    hunks: Hunk[];
    shownAt: string;
}

/**
 * Internal message representation for the chat thread.
 */
interface Message {
    id: string;
    role: 'user' | 'ai' | 'system';
    content: string;
    timestamp: Date;
    hasSuggestion?: boolean;
}

/**
 * Chat history entry formatted for LLM context injection.
 */
interface HistoryEntry {
    role: 'user' | 'model';
    content: string;
}

/**
 * Props for the AIChatPanel component.
 */
interface AIChatPanelProps {
    sessionId: string | null;
    activeFileId: string | null;
    activeContent: string;
    pendingSuggestion: PendingSuggestion | null;
    onSuggestion: (suggestion: PendingSuggestion) => void;
    onResolvePending: () => void;
}

const CODE_BLOCK_RE = /```[\w]*\n?([\s\S]*?)```/;

/**
 * Parses Markdown code blocks from LLM responses to isolate proposed code changes.
 */
function extractProposedCode(text: string): string | null {
    const match = CODE_BLOCK_RE.exec(text);
    return match ? match[1].trim() : null;
}

/**
 * Renders individual message bubbles with Markdown support for AI responses.
 */
function MessageContent({ content, role }: { content: string; role: 'user' | 'ai' | 'system' }) {
    if (role !== 'ai') {
        return <pre className="chat-text">{content}</pre>;
    }
    return (
        <div className="chat-markdown">
            <ReactMarkdown
                components={{
                    code({ children, ...props }) {
                        const isBlock = !props.ref;
                        return isBlock
                            ? <code className="chat-code-block">{children}</code>
                            : <code className="chat-inline-code" {...props}>{children}</code>;
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}

/**
 * Interactive chat interface for candidate-LLM collaboration.
 * 
 * Manages message history, handles prompt submission, and coordinates 
 * with the suggestion engine to provide inline code modifications.
 */
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
    const [retryPayload, setRetryPayload] = useState<{ text: string; history: HistoryEntry[] } | null>(null);
    const threadRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (threadRef.current) {
            threadRef.current.scrollTop = threadRef.current.scrollHeight;
        }
    }, [messages]);

    useEffect(() => {
        if (!sessionId) return;

        const loadHistory = async () => {
            try {
                const response = await api.get('/ai/history');
                const { messages: histMessages } = response.data as { messages: Array<{ role: string; content: string; timestamp: string; interaction_id: string }> };

                const formattedMessages: Message[] = histMessages.map((m) => ({
                    id: m.interaction_id,
                    role: m.role as 'user' | 'ai' | 'system',
                    content: m.content,
                    timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
                }));

                const formattedHistory: HistoryEntry[] = histMessages.map((m) => ({
                    role: m.role === 'ai' ? 'model' : 'user',
                    content: m.content,
                }));

                setMessages(formattedMessages);
                setHistory(formattedHistory);
            } catch {
                // Silently fail if history cannot be loaded
            }
        };

        void loadHistory();
    }, [sessionId]);

    const addMessage = (role: Message['role'], content: string, extra?: Partial<Message>): string => {
        const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setMessages((prev) => [...prev, { id, role, content, timestamp: new Date(), ...extra }]);
        return id;
    };

    const send = useCallback(async (retryText?: string, retryHistory?: HistoryEntry[]) => {
        const text = retryText ?? input.trim();
        if (!text || loading || !sessionId) return;

        if (!retryText) {
            setInput('');
            addMessage('user', text);
        }
        setLoading(true);
        setRetryPayload(null);

        if (pendingSuggestion) {
            onResolvePending();
        }

        const outgoingHistory = retryHistory ?? [...history];

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
            setRetryPayload({ text, history: outgoingHistory });
            addMessage('system', 'AI service unavailable. Please try again.');
        } finally {
            setLoading(false);
        }
    }, [input, loading, sessionId, activeFileId, activeContent, history, pendingSuggestion, onSuggestion, onResolvePending, showToast]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
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

            {retryPayload && (
                <div style={{ padding: '0.5rem 1rem', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'center' }}>
                    <Button variant="secondary" size="sm" onClick={() => void send(retryPayload.text, retryPayload.history)}>
                        Retry Connection
                    </Button>
                </div>
            )}

            <div className="chat-input-area">
                <Textarea
                    rows={3}
                    placeholder="Ask AI for help... (Enter to send, Shift+Enter for newline)"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    className="chat-textarea"
                />
                <div className="chat-send-row">
                    <span className="chat-hint">↵ to send, ⇧↵ for newline</span>
                    <Button onClick={() => void send()} disabled={loading || !input.trim() || !sessionId} size="sm">
                        {loading ? 'Sending...' : 'Send'}
                    </Button>
                </div>
            </div>
        </div>
    );
}
