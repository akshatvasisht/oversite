import { useCallback, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { AuthContext } from './context/auth';
import type { Role } from './context/auth';

/**
 * Provides world-level authentication state and session management.
 * 
 * Persists user credentials and active session identifiers to localStorage 
 * to ensure state continuity across page refreshes.
 */
export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [userId, setUserId] = useState<string | null>(localStorage.getItem('userId'));
    const [role, setRole] = useState<Role>((localStorage.getItem('userRole') as Role) || null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('authToken'));

    const [sessionId, setSessionIdState] = useState<string | null>(localStorage.getItem('sessionId'));

    const login = useCallback((user: string, r: Role, t: string) => {
        setUserId(user);
        setRole(r);
        setToken(t);
        localStorage.setItem('userId', user);
        localStorage.setItem('userRole', r || '');
        localStorage.setItem('authToken', t);
    }, []);

    const logout = useCallback(() => {
        setUserId(null);
        setRole(null);
        setToken(null);
        setSessionIdState(null);
        localStorage.removeItem('userId');
        localStorage.removeItem('userRole');
        localStorage.removeItem('authToken');
        localStorage.removeItem('sessionId');
    }, []);

    const setSessionId = useCallback((id: string | null) => {
        setSessionIdState(id);
        if (id) {
            localStorage.setItem('sessionId', id);
        } else {
            localStorage.removeItem('sessionId');
        }
    }, []);

    const value = useMemo(() => ({
        userId,
        role,
        token,
        sessionId,
        isAuthenticated: !!userId && !!token,
        login,
        logout,
        setSessionId
    }), [login, logout, role, token, sessionId, setSessionId, userId]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
