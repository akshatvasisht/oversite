import { createContext } from 'react';

export type Role = 'admin' | 'candidate' | null;

export interface AuthContextType {
    userId: string | null;
    role: Role;
    token: string | null;
    sessionId: string | null;
    isAuthenticated: boolean;
    login: (user: string, r: Role, t: string) => void;
    logout: () => void;
    setSessionId: (id: string | null) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

