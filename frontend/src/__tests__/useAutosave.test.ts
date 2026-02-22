import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useAutosave } from '../hooks/useAutosave';

describe('useAutosave', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('starts with idle status', () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { result } = renderHook(() =>
            useAutosave({ fileId: 'f1', content: 'hello', onSave, delayMs: 2000 })
        );
        expect(result.current.status).toBe('idle');
    });

    it('triggers onSave after debounce delay', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { rerender } = renderHook(
            ({ content }) => useAutosave({ fileId: 'f1', content, onSave, delayMs: 2000 }),
            { initialProps: { content: 'hello' } }
        );

        rerender({ content: 'hello world' });

        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        expect(onSave).toHaveBeenCalledWith('f1', 'hello world', 'debounce');
    });

    it('does not save when fileId is null', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { rerender } = renderHook(
            ({ content }) => useAutosave({ fileId: null, content, onSave, delayMs: 2000 }),
            { initialProps: { content: 'hello' } }
        );

        rerender({ content: 'hello world' });

        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        expect(onSave).not.toHaveBeenCalled();
    });

    it('debounces rapid changes — only saves once', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { rerender } = renderHook(
            ({ content }) => useAutosave({ fileId: 'f1', content, onSave, delayMs: 2000 }),
            { initialProps: { content: 'a' } }
        );

        rerender({ content: 'ab' });
        await act(async () => { vi.advanceTimersByTime(500); });

        rerender({ content: 'abc' });
        await act(async () => { vi.advanceTimersByTime(500); });

        rerender({ content: 'abcd' });
        await act(async () => { vi.advanceTimersByTime(2000); });

        expect(onSave).toHaveBeenCalledTimes(1);
        expect(onSave).toHaveBeenCalledWith('f1', 'abcd', 'debounce');
    });

    it('resets timer when content changes again mid-debounce', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { rerender } = renderHook(
            ({ content }) => useAutosave({ fileId: 'f1', content, onSave, delayMs: 2000 }),
            { initialProps: { content: 'hello' } }
        );

        rerender({ content: 'hello w' });
        await act(async () => { vi.advanceTimersByTime(1500); });
        expect(onSave).not.toHaveBeenCalled();

        rerender({ content: 'hello world' });
        await act(async () => { vi.advanceTimersByTime(2000); });
        expect(onSave).toHaveBeenCalledTimes(1);
    });
});
