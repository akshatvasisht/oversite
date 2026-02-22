import { useCallback, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { AuthContext } from './context/auth';
import type { Role } from './context/auth';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [userId, setUserId] = useState<string | null>(null);
    const [role, setRole] = useState<Role>(null);

    const [sessionId, setSessionIdState] = useState<string | null>(localStorage.getItem('sessionId'));

    const login = useCallback((user: string, r: Role) => {
        setUserId(user);
        setRole(r);
    }, []);

    const logout = useCallback(() => {
        setUserId(null);
        setRole(null);
        setSessionIdState(null);
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
        sessionId,
        isAuthenticated: !!userId,
        login,
        logout,
        setSessionId
    }), [login, logout, role, sessionId, setSessionId, userId]);

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
