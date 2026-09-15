"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowRight, LockKeyhole, Newspaper, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

import { api, prepareCsrf } from "@/lib/api";
import { useSession } from "@/components/session-provider";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Spinner } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); setSubmitting(true); try { await prepareCsrf(); await api.post("/auth/login", { username, password }); await refresh(); router.push("/"); } catch { setError("用户名或密码错误，请重新输入。"); } finally { setSubmitting(false); } };
  return <div className="grid min-h-[calc(100vh-9rem)] items-center gap-10 lg:grid-cols-[1fr_420px]"><section className="hidden lg:block"><div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Newspaper className="h-7 w-7" /></div><p className="mt-8 text-sm font-medium text-primary">校园报刊协作平台</p><h1 className="mt-3 max-w-lg text-5xl font-bold leading-tight tracking-tight">让每一期报刊，都有清晰的工作进度。</h1><p className="mt-5 max-w-md leading-7 text-muted-foreground">从投稿、审核到选录，在一个安静清晰的工作台里完成协作。</p></section><Card className="w-full"><CardHeader><CardTitle>登录 Current</CardTitle><CardDescription>使用你的校园账号继续。</CardDescription></CardHeader><CardContent><form className="space-y-4" onSubmit={submit}><label className="block text-sm font-medium"><span className="flex items-center gap-2"><UserRound className="h-4 w-4 text-muted-foreground" />用户名</span><Input className="mt-2" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label><label className="block text-sm font-medium"><span className="flex items-center gap-2"><LockKeyhole className="h-4 w-4 text-muted-foreground" />密码</span><Input className="mt-2" autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{error && <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}<Button className="w-full" disabled={submitting} type="submit">{submitting && <Spinner className="mr-2" />}登录<ArrowRight className="ml-2 h-4 w-4" /></Button></form><p className="mt-5 text-center text-xs text-muted-foreground"><Link className="hover:text-foreground" href="/about">了解 Current</Link></p></CardContent></Card></div>;
}
