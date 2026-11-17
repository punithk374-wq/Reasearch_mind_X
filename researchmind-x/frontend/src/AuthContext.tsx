/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import api from "./api";
import type { User } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem("token")));

  // On first load, if a token is saved, ask the backend who we are
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      return;
    }
    let active = true;
    const controller = new AbortController();
    api
      .get<User>("/api/auth/me", { signal: controller.signal })
      .then((res) => { if (active) setUser(res.data); })
      .catch(() => { if (active) localStorage.removeItem("token"); })
      .finally(() => { if (active) setLoading(false); });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const login = async (email: string, password: string) => {
    // The backend's login endpoint expects form data with a "username" field
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const res = await api.post<{ access_token: string }>("/api/auth/login", form);
    localStorage.setItem("token", res.data.access_token);

    const me = await api.get<User>("/api/auth/me");
    setUser(me.data);
  };

  const register = async (fullName: string, email: string, password: string) => {
    await api.post("/api/auth/register", {
      full_name: fullName,
      email,
      password,
    });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
