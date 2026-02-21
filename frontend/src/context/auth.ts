import { createContext } from 'react';

export type Role = 'admin' | 'candidate' | null;

export interface AuthContextType {
    userId: string | null;
    role: Role;
    sessionId: string | null;
    isAuthenticated: boolean;
    login: (user: string, r: Role) => void;
    logout: () => void;
    setSessionId: (id: string | null) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

