import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

type Role = 'admin' | 'candidate' | null;

interface AuthContextType {
    userId: string | null;
    role: Role;
    sessionId: string | null;
    isAuthenticated: boolean;
    login: (user: string, r: Role) => void;
    logout: () => void;
    setSessionId: (id: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

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
    }

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

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
