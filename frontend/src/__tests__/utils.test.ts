import { describe, it, expect } from 'vitest';
import { cn } from '../lib/utils';

describe('cn utility', () => {
    it('joins class names', () => {
        expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('filters out falsy values', () => {
        expect(cn('foo', null, undefined, false, 'bar')).toBe('foo bar');
    });

    it('returns empty string for all falsy', () => {
        expect(cn(null, undefined, false)).toBe('');
    });

    it('handles single class', () => {
        expect(cn('only')).toBe('only');
    });

    it('handles no arguments', () => {
        expect(cn()).toBe('');
    });
});
