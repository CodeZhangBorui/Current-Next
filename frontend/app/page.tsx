"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarClock, CheckCircle2, CircleDashed, FilePlus2, Megaphone, RefreshCw, Search } from "lucide-react";

import { api } from "@/lib/api";
import type { Issue } from "@/lib/types";
import { useSession } from "@/components/session-provider";
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Spinner } from "@/components/ui";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

export default function HomePage() {
  const { user } = useSession();
  const [issues, setIssues] = useState<Issue[]>([]);
  const [announcement, setAnnouncement] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "published">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [issueResponse, announcementResponse] = await Promise.all([api.get("/issues"), api.get("/announcement")]);
      setIssues(issueResponse.data);
      setAnnouncement(announcementResponse.data.content || "");
    } catch {
      setError("期刊暂时加载失败，请检查网络后重试。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (user) load(); }, [user]);

  const filteredIssues = useMemo(() => issues.filter((issue) => {
    const matchesQuery = `${issue.id} ${issue.subject.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    const matchesFilter = filter === "all" || (filter === "published" ? issue.published : !issue.published);
    return matchesQuery && matchesFilter;
  }), [filter, issues, query]);
  const openCount = issues.filter((issue) => !issue.published).length;
  const publishedCount = issues.filter((issue) => issue.published).length;

  if (!user) return null;
  return <div className="space-y-8">
    <section className="flex flex-col justify-between gap-6 rounded-xl border bg-card p-6 shadow-sm sm:flex-row sm:items-end"><div><p className="text-sm font-medium text-primary">Current / 工作台</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">你好，{user.username}</h1><p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">在这里查看最新期刊、跟进投稿进度，并提交下一篇文章。</p></div><div className="flex flex-wrap gap-2"><Link href="/statistic"><Button variant="outline">查看统计<ArrowRight className="ml-2 h-4 w-4" /></Button></Link>{user.is_staff && <Link href="/newissue"><Button><FilePlus2 className="mr-2 h-4 w-4" />创建期刊</Button></Link>}</div></section>
    {announcement && <Card className="border-primary/20 bg-primary/[0.03]"><CardContent className="flex gap-3 p-4"><Megaphone className="mt-0.5 h-5 w-5 shrink-0 text-primary" /><div><p className="text-sm font-semibold">站点公告</p><p className="mt-1 text-sm leading-6 text-muted-foreground">{announcement}</p></div></CardContent></Card>}
    <section className="grid gap-3 sm:grid-cols-3"><SummaryCard label="全部期刊" value={issues.length} icon={<CalendarClock className="h-5 w-5" />} /><SummaryCard label="征稿中" value={openCount} icon={<CircleDashed className="h-5 w-5" />} accent="text-primary" /><SummaryCard label="已出版" value={publishedCount} icon={<CheckCircle2 className="h-5 w-5" />} accent="text-green-600" /></section>
    <section className="space-y-4"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="text-xl font-semibold">期刊列表</h2><p className="mt-1 text-sm text-muted-foreground">选择一期，查看版面和稿件状态。</p></div><div className="relative w-full sm:w-64"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><Input className="pl-9" placeholder="搜索期数或版面" value={query} onChange={(event) => setQuery(event.target.value)} /></div></div><div className="flex gap-2 border-b pb-3"><FilterButton active={filter === "all"} onClick={() => setFilter("all")}>全部</FilterButton><FilterButton active={filter === "open"} onClick={() => setFilter("open")}>征稿中</FilterButton><FilterButton active={filter === "published"} onClick={() => setFilter("published")}>已出版</FilterButton></div>{loading ? <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground"><Spinner />正在加载期刊...</div> : error ? <Card><CardContent className="flex flex-col items-center gap-3 p-10 text-center"><p className="text-sm text-destructive">{error}</p><Button variant="outline" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />重试</Button></CardContent></Card> : filteredIssues.length === 0 ? <Card><CardContent className="p-10 text-center"><FilePlus2 className="mx-auto h-8 w-8 text-muted-foreground" /><p className="mt-3 font-medium">没有找到匹配的期刊</p><p className="mt-1 text-sm text-muted-foreground">换一个关键词或筛选条件试试。</p></CardContent></Card> : <div className="grid gap-3 lg:grid-cols-2">{filteredIssues.map((issue) => <IssueCard issue={issue} key={issue.id} />)}</div>}</section>
  </div>;
}

function SummaryCard({ label, value, icon, accent = "text-foreground" }: { label: string; value: number; icon: React.ReactNode; accent?: string }) { return <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-sm text-muted-foreground">{label}</p><p className={`mt-1 text-2xl font-bold ${accent}`}>{value}</p></div><div className={`rounded-md bg-muted p-2 ${accent}`}>{icon}</div></CardContent></Card>; }
function FilterButton({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) { return <button className={`rounded-md px-3 py-1.5 text-sm ${active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`} onClick={onClick}>{children}</button>; }
function IssueCard({ issue }: { issue: Issue }) { return <Link href={`/issue/${issue.id}`}><Card className="group h-full transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md"><CardHeader className="flex-row items-start justify-between space-y-0 pb-3"><div className="flex items-center gap-3"><div className={`rounded-md p-2 ${issue.published ? "bg-green-100 text-green-700" : "bg-primary/10 text-primary"}`}>{issue.published ? <CheckCircle2 className="h-5 w-5" /> : <CircleDashed className="h-5 w-5" />}</div><div><CardTitle className="text-base">第 {issue.id} 期</CardTitle><CardDescription className="mt-1">{issue.published ? "已出版" : "正在征稿"}</CardDescription></div></div><ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" /></CardHeader><CardContent className="flex items-center justify-between pt-0 text-sm"><span className="text-muted-foreground">{issue.published ? "查看已发布 PDF" : `截稿日期：${formatDate(issue.deadline)}`}</span><Badge variant={issue.published ? "success" : "warning"}>{issue.published ? "已出版" : "征稿中"}</Badge></CardContent></Card></Link>; }
