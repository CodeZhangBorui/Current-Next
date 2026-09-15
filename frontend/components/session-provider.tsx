"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api, prepareCsrf } from "@/lib/api";
import type { User } from "@/lib/types";

type SessionContextValue = { user: User | null; loading: boolean; refresh: () => Promise<void>; logout: () => Promise<void> };
const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = async () => {
    try { const response = await api.get("/auth/me"); setUser(response.data.user); } catch { setUser(null); } finally { setLoading(false); }
  };
  useEffect(() => { prepareCsrf().finally(refresh); }, []);
  const logout = async () => { await api.post("/auth/logout"); setUser(null); };
  return <SessionContext.Provider value={{ user, loading, refresh, logout }}>{children}</SessionContext.Provider>;
}

export function useSession() { const value = useContext(SessionContext); if (!value) throw new Error("useSession must be used inside SessionProvider"); return value; }
