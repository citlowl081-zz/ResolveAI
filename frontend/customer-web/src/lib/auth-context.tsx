"use client";
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { auth, setTokens, clearTokens, loadTokens, onUnauthorized, type UserInfo } from "./api";

interface AuthState {
  user: UserInfo | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null, loading: true,
  login: async () => {}, register: async () => {}, logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const protectedPaths = ["/agent", "/orders", "/tickets", "/memories", "/approvals", "/account"];
  const isProtected = protectedPaths.some(
    path => pathname === path || pathname.startsWith(`${path}/`)
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    router.replace("/login");
  }, [router]);

  const handleUnauthorized = useCallback(() => {
    clearTokens();
    setUser(null);
    if (isProtected) router.replace("/login");
  }, [isProtected, router]);

  useEffect(() => {
    const hasTokens = loadTokens();
    onUnauthorized(handleUnauthorized);
    if (!hasTokens) {
      setLoading(false);
      return;
    }
    auth.me()
      .then(r => { if (r.success && r.data) setUser(r.data); })
      .catch(() => handleUnauthorized())
      .finally(() => setLoading(false));
  }, [handleUnauthorized]);

  useEffect(() => {
    if (!loading && !user && isProtected) router.replace("/login");
  }, [isProtected, loading, router, user]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await auth.login(email, password);
    if (r.success && r.data) {
      setTokens(r.data.access_token, r.data.refresh_token);
      setUser(r.data.user);
    } else throw new Error("登录失败，请检查账号和密码");
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    const r = await auth.register(email, password, name);
    if (!r.success) throw new Error("注册失败，请检查填写信息");
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
