import { useState } from 'react';
import type { ReactNode } from 'react';
import { AuthContext } from './context/auth';
import type { Role } from './context/auth';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [userId, setUserId] = useState<string | null>(null);
    const [role, setRole] = useState<Role>(null);
    const [sessionId, setSessionIdState] = useState<string | null>(localStorage.getItem('sessionId'));

    const login = (user: string, r: Role) => {
        setUserId(user);
        setRole(r);
    };

    const logout = () => {
        setUserId(null);
        setRole(null);
        setSessionIdState(null);
        localStorage.removeItem('sessionId');
    };

    const setSessionId = (id: string | null) => {
        setSessionIdState(id);
        if (id) {
            localStorage.setItem('sessionId', id);
        } else {
            localStorage.removeItem('sessionId');
        }
    };

    const value = {
        userId,
        role,
        sessionId,
        isAuthenticated: !!userId,
        login,
        logout,
        setSessionId
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
