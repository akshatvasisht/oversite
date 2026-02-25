import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import AIChatPanel from '../components/AIChatPanel';
import { ToastProvider } from '../context/ToastContext';

// Mock the api module
vi.mock('../api', () => ({
    default: {
        post: vi.fn(),
    },
}));

import api from '../api';
const mockPost = vi.mocked(api.post);

const defaultProps = {
    sessionId: 'test-session-id',
    activeFileId: 'file-123',
    activeContent: 'def solve():\n    pass\n',
    pendingSuggestion: null,
    onSuggestion: vi.fn(),
    onResolvePending: vi.fn(),
};

const renderWithToast = (ui: React.ReactElement) => {
    return render(<ToastProvider>{ui}</ToastProvider>);
};

describe('AIChatPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders empty state message', () => {
        renderWithToast(<AIChatPanel {...defaultProps} />);
        expect(screen.getByText(/Ask for implementation hints/i)).toBeInTheDocument();
    });

    it('renders input textarea and send button', () => {
        renderWithToast(<AIChatPanel {...defaultProps} />);
        expect(screen.getByPlaceholderText(/Ask AI for help/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });

    it('send button is disabled when input is empty', () => {
        renderWithToast(<AIChatPanel {...defaultProps} />);
        expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('send button is disabled when sessionId is null', () => {
        renderWithToast(<AIChatPanel {...defaultProps} sessionId={null} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'hello' } });
        expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('send button enables when input has text', () => {
        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'help me' } });
        expect(screen.getByRole('button', { name: /send/i })).not.toBeDisabled();
    });

    it('shows user message in thread on send', async () => {
        mockPost.mockResolvedValueOnce({
            data: { interaction_id: 'int-1', response: 'Hello!', has_code_changes: false },
        });

        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'help me solve this' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        expect(screen.getByText('help me solve this')).toBeInTheDocument();
    });

    it('shows AI response after successful API call', async () => {
        mockPost.mockResolvedValueOnce({
            data: { interaction_id: 'int-1', response: 'Here is my answer.', has_code_changes: false },
        });

        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'help' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(screen.getByText('Here is my answer.')).toBeInTheDocument();
        });
    });

    it('shows error message when API call fails', async () => {
        mockPost.mockRejectedValueOnce(new Error('Network error'));

        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'help' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(screen.getByText(/AI service unavailable/i)).toBeInTheDocument();
        });
    });

    it('clears input after sending', async () => {
        mockPost.mockResolvedValueOnce({
            data: { interaction_id: 'int-1', response: 'OK', has_code_changes: false },
        });

        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i) as HTMLTextAreaElement;
        fireEvent.change(textarea, { target: { value: 'hello' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        expect(textarea.value).toBe('');
    });

    it('calls POST /suggestions when response has code changes', async () => {
        const responseWithCode = 'Here is the fix:\n```python\ndef solve():\n    return 42\n```';
        mockPost
            .mockResolvedValueOnce({
                data: { interaction_id: 'int-1', response: responseWithCode, has_code_changes: true },
            })
            .mockResolvedValueOnce({
                data: { suggestion_id: 'sug-1', hunks: [], shown_at: new Date().toISOString() },
            });

        renderWithToast(<AIChatPanel {...defaultProps} />);
        fireEvent.change(screen.getByPlaceholderText(/Ask AI for help/i), { target: { value: 'fix it' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledWith('/suggestions', expect.objectContaining({
                interaction_id: 'int-1',
                file_id: 'file-123',
                original_content: defaultProps.activeContent,
            }));
        });
    });

    it('calls onSuggestion callback with returned suggestion data', async () => {
        const responseWithCode = 'Fix:\n```python\ndef solve():\n    return 42\n```';
        const suggestionData = { suggestion_id: 'sug-1', hunks: [{ start_line: 1, end_line: 1, original_code: 'pass', proposed_code: 'return 42' }], shown_at: '2024-01-01T00:00:00Z' };
        mockPost
            .mockResolvedValueOnce({ data: { interaction_id: 'int-1', response: responseWithCode, has_code_changes: true } })
            .mockResolvedValueOnce({ data: suggestionData });

        const onSuggestion = vi.fn();
        renderWithToast(<AIChatPanel {...defaultProps} onSuggestion={onSuggestion} />);
        fireEvent.change(screen.getByPlaceholderText(/Ask AI for help/i), { target: { value: 'fix' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(onSuggestion).toHaveBeenCalledWith(expect.objectContaining({
                suggestionId: 'sug-1',
            }));
        });
    });

    it('shows pending suggestion banner when pendingSuggestion is set', () => {
        const pending = { suggestionId: 'sug-1', hunks: [], shownAt: '2024-01-01T00:00:00Z' };
        renderWithToast(<AIChatPanel {...defaultProps} pendingSuggestion={pending} />);
        expect(screen.getByText(/Suggestion pending in editor/i)).toBeInTheDocument();
    });

    it('calls onResolvePending before sending when suggestion is pending', async () => {
        mockPost.mockResolvedValueOnce({
            data: { interaction_id: 'int-1', response: 'OK', has_code_changes: false },
        });

        const onResolvePending = vi.fn();
        const pending = { suggestionId: 'sug-1', hunks: [], shownAt: '2024-01-01T00:00:00Z' };
        renderWithToast(<AIChatPanel {...defaultProps} pendingSuggestion={pending} onResolvePending={onResolvePending} />);
        fireEvent.change(screen.getByPlaceholderText(/Ask AI for help/i), { target: { value: 'next question' } });
        fireEvent.click(screen.getByRole('button', { name: /send/i }));

        await waitFor(() => {
            expect(onResolvePending).toHaveBeenCalled();
        });
    });

    it('sends Cmd+Enter to submit', async () => {
        mockPost.mockResolvedValueOnce({
            data: { interaction_id: 'int-1', response: 'Hi', has_code_changes: false },
        });

        renderWithToast(<AIChatPanel {...defaultProps} />);
        const textarea = screen.getByPlaceholderText(/Ask AI for help/i);
        fireEvent.change(textarea, { target: { value: 'hello' } });
        fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true });

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledWith('/ai/chat', expect.any(Object));
        });
    });
});
