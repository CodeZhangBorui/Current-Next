"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CircleCheck, CircleDashed, Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { Issue } from "@/lib/types";
import { useSession } from "@/components/session-provider";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

export default function HomePage() {
  const { user } = useSession(); const [issues, setIssues] = useState<Issue[]>([]); const [announcement, setAnnouncement] = useState("");
  useEffect(() => { if (!user) return; Promise.all([api.get("/issues"), api.get("/announcement")]).then(([issueRes, announcementRes]) => { setIssues(issueRes.data); setAnnouncement(announcementRes.data.content); }); }, [user]);
  if (!user) return <div className="mx-auto max-w-xl py-20 text-center"><h1 className="text-4xl font-bold">Current</h1><p className="mt-3 text-muted-foreground">校园报刊投稿与编辑平台</p><Link href="/login"><Button className="mt-8">登录</Button></Link></div>;
  return <div className="space-y-8"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm text-muted-foreground">欢迎回来，{user.username}</p><h1 className="mt-1 text-3xl font-bold">期刊工作台</h1></div>{user.is_staff && <Link href="/admin/"><Button><Plus className="mr-2 h-4 w-4" />管理后台</Button></Link>}</div>{announcement && <Card><CardContent className="p-4 text-sm">{announcement}</CardContent></Card>}<section><div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">全部期刊</h2><span className="text-sm text-muted-foreground">{issues.length} 期</span></div><div className="grid gap-3">{issues.map((issue) => <Link href={`/issue/${issue.id}`} key={issue.id}><Card className="transition-colors hover:border-primary"><CardHeader className="flex-row items-center justify-between pb-3"><CardTitle className="flex items-center gap-2 text-base">{issue.published ? <CircleCheck className="h-5 w-5 text-green-600" /> : <CircleDashed className="h-5 w-5 text-primary" />}第 {issue.id} 期</CardTitle><ArrowRight className="h-4 w-4 text-muted-foreground" /></CardHeader><CardContent className="pt-0 text-sm text-muted-foreground">{issue.published ? "已出版" : `截稿日期：${new Date(issue.deadline).toLocaleDateString("zh-CN")}`}</CardContent></Card></Link>)}{issues.length === 0 && <Card><CardContent className="p-8 text-center text-muted-foreground">暂无期刊</CardContent></Card>}</div></section></div>;
}
