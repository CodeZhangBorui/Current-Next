"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/components/session-provider";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@/components/ui";

export default function SettingsPage() { const { user, logout } = useSession(); const [oldPassword, setOldPassword] = useState(""); const [newPassword, setNewPassword] = useState(""); const [message, setMessage] = useState(""); const submit = async (event: FormEvent) => { event.preventDefault(); try { await api.post("/auth/password", { old_password: oldPassword, new_password: newPassword }); setMessage("密码修改成功，请重新登录。"); setTimeout(logout, 800); } catch { setMessage("密码修改失败，请检查原密码。"); } }; return <div className="max-w-2xl space-y-5"><h1 className="text-3xl font-bold">个人设置</h1><Card><CardHeader><CardTitle>个人信息</CardTitle></CardHeader><CardContent className="space-y-2 text-sm"><p>姓名：{user?.username}</p><p>年级：{user?.grade}</p><p>班级：{user?.classnum}</p></CardContent></Card><Card><CardHeader><CardTitle>修改密码</CardTitle></CardHeader><CardContent><form className="space-y-4" onSubmit={submit}><Input type="password" placeholder="原密码" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required /><Input type="password" placeholder="新密码" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} /><Button type="submit">确认修改</Button>{message && <p className="text-sm text-muted-foreground">{message}</p>}</form></CardContent></Card></div>; }
