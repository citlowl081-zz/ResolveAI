"use client";
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { adminAuth, setTokens, clearTokens, loadTokens, onUnauthorized, type UserInfo } from "./api";

interface AuthState {
  user: UserInfo | null; loading: boolean;
  login: (email: string, password: string) => Promise<void>; logout: () => void;
}
const AuthContext = createContext<AuthState>({ user: null, loading: true, login: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const logout = useCallback(() => { clearTokens(); setUser(null); }, []);
  useEffect(() => { loadTokens(); onUnauthorized(logout); adminAuth.me().then(r => { if (r.success && r.data) setUser(r.data); }).catch(() => logout()).finally(() => setLoading(false)); }, [logout]);
  const login = useCallback(async (email: string, password: string) => { const r = await adminAuth.login(email, password); if (r.success && r.data) { setTokens(r.data.access_token, r.data.refresh_token); setUser(r.data.user); } else throw new Error("Login failed"); }, []);
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
