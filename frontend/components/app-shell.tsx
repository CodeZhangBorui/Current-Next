"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Menu, Newspaper, Settings, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { Button, Spinner } from "@/components/ui";
import { useSession } from "@/components/session-provider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useSession();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  if (loading) return <main className="flex min-h-screen items-center justify-center gap-2 text-sm text-muted-foreground"><Spinner />正在加载 Current...</main>;
  const navigation = <><Link onClick={() => setOpen(false)} href="/" className="rounded-md px-3 py-2 text-sm hover:bg-muted">期刊</Link><Link onClick={() => setOpen(false)} href="/statistic" className="rounded-md px-3 py-2 text-sm hover:bg-muted">统计</Link><Link onClick={() => setOpen(false)} href="/settings" className="rounded-md px-3 py-2 text-sm hover:bg-muted"><Settings className="mr-1 inline h-4 w-4" />设置</Link>{user?.is_staff && <Link onClick={() => setOpen(false)} href="/admin/" className="rounded-md px-3 py-2 text-sm hover:bg-muted"><ShieldCheck className="mr-1 inline h-4 w-4" />管理</Link>}<Button size="sm" variant="ghost" onClick={() => { setOpen(false); logout(); }}><LogOut className="mr-2 h-4 w-4" />退出</Button></>;
  return <div className="min-h-screen bg-background"><header className="sticky top-0 z-20 border-b bg-card/95 backdrop-blur"><div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4"><Link href="/" className="flex items-center gap-2 font-semibold" onClick={() => setOpen(false)}><span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground transition-transform duration-300 hover:rotate-6"><Newspaper className="h-4 w-4" /></span><span>Current</span></Link>{user && <><nav className="hidden items-center gap-1 md:flex">{navigation}</nav><Button className="md:hidden" variant="ghost" size="icon" aria-label={open ? "关闭菜单" : "打开菜单"} onClick={() => setOpen(!open)}>{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</Button></>}</div>{user && open && <nav className="flex flex-col border-t px-4 py-3 md:hidden">{navigation}</nav>}</header><main className="mx-auto max-w-6xl px-4 py-8"><div key={pathname} className="page-transition">{!user && pathname !== "/login" ? <div className="mx-auto max-w-md rounded-lg border bg-card p-8 text-center motion-card"><h1 className="text-xl font-semibold">请先登录</h1><p className="mt-2 text-sm text-muted-foreground">登录后即可查看期刊、提交稿件和管理个人资料。</p><Link href="/login"><Button className="mt-6">前往登录</Button></Link></div> : children}</div></main></div>;
}
