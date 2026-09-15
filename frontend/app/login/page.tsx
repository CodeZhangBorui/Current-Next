"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, prepareCsrf } from "@/lib/api";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@/components/ui";
import { useSession } from "@/components/session-provider";

export default function LoginPage() {
  const router = useRouter(); const { refresh } = useSession(); const [username, setUsername] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState("");
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); try { await prepareCsrf(); await api.post("/auth/login", { username, password }); await refresh(); router.push("/"); } catch { setError("用户名或密码错误。"); } };
  return <div className="mx-auto max-w-md pt-12"><Card><CardHeader><CardTitle>登录 Current</CardTitle></CardHeader><CardContent><form className="space-y-4" onSubmit={submit}><label className="block text-sm">用户名<Input className="mt-2" value={username} onChange={(e) => setUsername(e.target.value)} required /></label><label className="block text-sm">密码<Input className="mt-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>{error && <p className="text-sm text-destructive">{error}</p>}<Button className="w-full" type="submit">登录</Button></form></CardContent></Card></div>;
}
