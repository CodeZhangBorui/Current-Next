"use client";

import Link from "next/link";
import { LogOut, Newspaper, Settings, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui";
import { useSession } from "@/components/session-provider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useSession();
  if (loading) return <main className="mx-auto max-w-5xl p-8 text-muted-foreground">正在加载...</main>;
  return <div className="min-h-screen bg-background"><header className="border-b bg-card"><div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4"><Link href="/" className="flex items-center gap-2 font-semibold"><Newspaper className="h-5 w-5 text-primary" /> Current</Link>{user && <nav className="flex items-center gap-1"><Link href="/" className="rounded-md px-3 py-2 text-sm hover:bg-muted">期刊</Link><Link href="/settings" className="rounded-md px-3 py-2 text-sm hover:bg-muted"><Settings className="mr-1 inline h-4 w-4" />设置</Link>{user.is_staff && <Link href="/admin/" className="rounded-md px-3 py-2 text-sm hover:bg-muted"><ShieldCheck className="mr-1 inline h-4 w-4" />管理</Link>}<Button variant="ghost" onClick={() => logout()}><LogOut className="mr-2 h-4 w-4" />退出</Button></nav>}</div></header><main className="mx-auto max-w-5xl px-4 py-8">{children}</main></div>;
}
