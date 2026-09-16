"use client";

import { useCallback, useEffect, useState } from "react";
import { Link } from "@/components/page-transition";
import { ArrowLeft, BarChart3, BookOpenCheck, Clock3, FileCheck2, FileText, MessageSquare, RefreshCw, RotateCcw, Users } from "lucide-react";

import { api } from "@/lib/api";
import type { EntryStatus, Statistics } from "@/lib/types";
import { useSession } from "@/components/session-provider";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Spinner } from "@/components/ui";

const numberFormatter = new Intl.NumberFormat("zh-CN");
const statusMeta: Array<{ key: EntryStatus; label: string; color: string; bar: string }> = [
  { key: "pending", label: "待投稿", color: "text-slate-600", bar: "bg-slate-400" },
  { key: "created", label: "等待审核", color: "text-amber-700", bar: "bg-amber-400" },
  { key: "reviewed", label: "审核完成", color: "text-blue-700", bar: "bg-blue-500" },
  { key: "selected", label: "已关闭并合并", color: "text-green-700", bar: "bg-green-500" },
  { key: "invalid", label: "已关闭为无效", color: "text-red-700", bar: "bg-red-500" },
];

function formatNumber(value: number) { return numberFormatter.format(value); }
function formatDuration(value: number | null) {
  if (value === null) return "暂无数据";
  if (value * 60 < 1) return "少于 1 分钟";
  if (value < 1) return `${Math.round(value * 60)} 分钟`;
  if (value < 48) return `${value} 小时`;
  return `${(value / 24).toFixed(1)} 天`;
}

export default function StatisticPage() {
  const { user } = useSession();
  const [data, setData] = useState<Statistics | null>(null);
  const [rankingPeriod, setRankingPeriod] = useState<Statistics["ranking_period"]>("latest");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try { setData((await api.get<Statistics>("/statistics", { params: { ranking_period: rankingPeriod } })).data); }
    catch { setError("统计数据暂时无法加载，请检查网络后重试。"); }
    finally { setLoading(false); }
  }, [rankingPeriod]);
  useEffect(() => { if (user) load(); }, [load, user]);

  if (!user) return null;
  if (loading && !data) return <div className="flex min-h-72 items-center justify-center gap-2 text-sm text-muted-foreground"><Spinner />正在汇总统计数据...</div>;
  if (!data) return <Card><CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 p-8 text-center"><BarChart3 className="h-9 w-9 text-muted-foreground" /><p className="text-sm text-destructive">{error}</p><Button variant="outline" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />重新加载</Button></CardContent></Card>;

  const closed = data.status_counts.selected + data.status_counts.invalid;
  const mergeRate = closed ? Math.round((data.status_counts.selected / closed) * 100) : 0;
  return <div className="space-y-7">
    <header className="flex flex-col justify-between gap-4 border-b pb-6 sm:flex-row sm:items-end"><div><Link className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" href="/"><ArrowLeft className="h-4 w-4" />返回工作台</Link><h1 className="mt-4 text-3xl font-bold">统计概览</h1><p className="mt-2 text-sm text-muted-foreground">查看投稿规模、审核进度和各期刊的协作情况。</p></div><Button disabled={loading} variant="outline" onClick={load}>{loading ? <Spinner className="mr-2" /> : <RefreshCw className="mr-2 h-4 w-4" />}刷新数据</Button></header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="稿件总数" value={formatNumber(data.summary.entries)} detail={`${formatNumber(data.summary.words)} 字`} icon={<FileText className="h-5 w-5" />} />
      <Metric label="已出版期刊" value={`${data.summary.published_issues} / ${data.summary.issues}`} detail="已出版 / 全部" icon={<BookOpenCheck className="h-5 w-5" />} accent="text-green-600" />
      <Metric label="合并率" value={`${mergeRate}%`} detail={`已处理 ${closed} 篇`} icon={<FileCheck2 className="h-5 w-5" />} accent="text-blue-600" />
      <Metric label="协作记录" value={formatNumber(data.summary.versions + data.summary.comments)} detail={`${data.summary.versions} 个版本 · ${data.summary.comments} 条留言`} icon={<MessageSquare className="h-5 w-5" />} accent="text-violet-600" />
    </section>

    <section className="grid gap-3 sm:grid-cols-4"><PersonalMetric label="我的投稿" value={data.personal.submitted} /><PersonalMetric label="我的稿件已合并" value={data.personal.merged} /><PersonalMetric label="待我方审核" value={data.personal.reviewing} highlight={data.personal.reviewing > 0} /><PersonalMetric label="待我方决策" value={data.personal.awaiting_decision} highlight={data.personal.awaiting_decision > 0} /></section>

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
      <Card><CardHeader><CardTitle className="text-base">稿件状态</CardTitle><CardDescription>所有期刊中的当前状态分布</CardDescription></CardHeader><CardContent className="space-y-4">{statusMeta.map((status) => <StatusRow key={status.key} label={status.label} value={data.status_counts[status.key]} total={data.summary.entries} color={status.color} bar={status.bar} />)}</CardContent></Card>
      <Card><CardHeader><CardTitle className="text-base">处理效率</CardTitle><CardDescription>基于具有完整时间记录的稿件计算</CardDescription></CardHeader><CardContent className="grid gap-5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2"><WorkflowMetric icon={<Clock3 className="h-5 w-5 text-blue-600" />} label="平均审核耗时" value={formatDuration(data.workflow.average_review_hours)} /><WorkflowMetric icon={<FileCheck2 className="h-5 w-5 text-green-600" />} label="平均终审耗时" value={formatDuration(data.workflow.average_decision_hours)} /><WorkflowMetric icon={<RotateCcw className="h-5 w-5 text-amber-600" />} label="退回重新审核" value={`${data.workflow.returned_reviews} 次`} /><WorkflowMetric icon={<RefreshCw className="h-5 w-5 text-red-600" />} label="关闭后重新打开" value={`${data.workflow.reopened_entries} 次`} /></CardContent></Card>
    </section>

    <IssueTrend issues={data.issues} />
    <section className="space-y-3" aria-busy={loading}><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="text-lg font-semibold">贡献排行榜</h2><p className="mt-1 text-sm text-muted-foreground">未关联用户的旧数据不会进入排行。</p></div><div className="inline-flex w-fit rounded-md border bg-card p-1" aria-label="排行榜统计范围">{([['latest', '最近一期'], ['recent3', '最近三期'], ['all', '所有']] as const).map(([value, label]) => <button disabled={loading} className={`rounded-sm px-3 py-1.5 text-sm transition-colors disabled:opacity-60 ${rankingPeriod === value ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`} key={value} onClick={() => setRankingPeriod(value)}>{label}</button>)}</div></div><div className={`grid gap-5 transition-opacity lg:grid-cols-2 ${loading ? "opacity-60" : "opacity-100"}`}><Ranking title="投稿贡献" description="按投稿篇数排序" icon={<FileText className="h-5 w-5 text-primary" />} empty="此范围内暂无投稿记录" rows={data.contributors.map((item) => ({ name: item.username, primary: `${item.entries} 篇`, secondary: `${formatNumber(item.words)} 字 · ${item.merged} 篇已合并` }))} /><Ranking title="编辑协作" description="审核、终审、留言和修订版本记录" icon={<Users className="h-5 w-5 text-primary" />} empty="此范围内暂无编辑协作记录" rows={data.collaborators.map((item) => ({ name: item.username, primary: `${item.reviews + item.merges} 次处理`, secondary: `审核 ${item.reviews} · 合并 ${item.merges} · 留言 ${item.comments} · 修订 ${item.versions}` }))} /></div></section>
    <Card><CardHeader><CardTitle className="text-base">版面分布</CardTitle><CardDescription>各版投稿数量、合并数量和总字数</CardDescription></CardHeader><CardContent>{data.pages.length ? <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{data.pages.map((page) => <div className="rounded-md border p-4" key={page.page}><p className="text-sm font-medium">第 {page.page} 版</p><p className="mt-3 text-2xl font-bold">{page.total}</p><p className="mt-1 text-xs text-muted-foreground">合并 {page.merged} 篇 · {formatNumber(page.words || 0)} 字</p></div>)}</div> : <EmptyText>暂无版面数据</EmptyText>}</CardContent></Card>
  </div>;
}

function Metric({ label, value, detail, icon, accent = "text-primary" }: { label: string; value: string; detail: string; icon: React.ReactNode; accent?: string }) { return <Card><CardContent className="flex items-start justify-between p-5"><div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div><div className={`rounded-md bg-muted p-2 ${accent}`}>{icon}</div></CardContent></Card>; }
function PersonalMetric({ label, value, highlight = false }: { label: string; value: number; highlight?: boolean }) { return <div className={`flex items-center justify-between rounded-md border px-4 py-3 ${highlight ? "border-amber-300 bg-amber-50" : "bg-card"}`}><span className="text-sm text-muted-foreground">{label}</span><span className={`text-lg font-bold ${highlight ? "text-amber-700" : ""}`}>{value}</span></div>; }
function StatusRow({ label, value, total, color, bar }: { label: string; value: number; total: number; color: string; bar: string }) { const percentage = total ? Math.round((value / total) * 100) : 0; return <div><div className="mb-1.5 flex items-center justify-between text-sm"><span className={color}>{label}</span><span><strong>{value}</strong><span className="ml-2 text-xs text-muted-foreground">{percentage}%</span></span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${bar}`} style={{ width: `${percentage}%` }} /></div></div>; }
function WorkflowMetric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex gap-3"><div className="rounded-md bg-muted p-2">{icon}</div><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></div></div>; }

function IssueTrend({ issues }: { issues: Statistics["issues"] }) {
  const recent = issues.slice(-12);
  const max = Math.max(1, ...recent.map((issue) => issue.total));
  if (!recent.length) return <Card><CardHeader><CardTitle className="text-base">跨期趋势</CardTitle></CardHeader><CardContent><EmptyText>暂无期刊数据</EmptyText></CardContent></Card>;
  return <Card><CardHeader><CardTitle className="text-base">跨期趋势</CardTitle><CardDescription>最近 {recent.length} 期的稿件数量及当前状态</CardDescription></CardHeader><CardContent><div className="overflow-x-auto pb-2"><div className="flex h-56 min-w-[640px] items-end gap-3 border-b px-2">{recent.map((issue) => { const height = Math.max(6, (issue.total / max) * 160); return <Link className="group flex min-w-10 flex-1 flex-col items-center" href={`/issue/${issue.id}`} key={issue.id}><span className="mb-2 text-xs font-semibold">{issue.total}</span><div className="flex w-full max-w-12 flex-col-reverse overflow-hidden rounded-t-sm bg-muted transition-opacity group-hover:opacity-80" style={{ height }} title={`第 ${issue.id} 期，共 ${issue.total} 篇`}><TrendPart count={issue.pending} total={issue.total} color="bg-slate-400" /><TrendPart count={issue.waiting} total={issue.total} color="bg-amber-400" /><TrendPart count={issue.reviewed} total={issue.total} color="bg-blue-500" /><TrendPart count={issue.merged} total={issue.total} color="bg-green-500" /><TrendPart count={issue.invalid} total={issue.total} color="bg-red-500" /></div><span className="mt-2 whitespace-nowrap text-xs text-muted-foreground">第 {issue.id} 期</span></Link>; })}</div></div><div className="mt-5 flex flex-wrap gap-x-5 gap-y-2">{statusMeta.map((item) => <span className="flex items-center gap-1.5 text-xs text-muted-foreground" key={item.key}><span className={`h-2.5 w-2.5 rounded-sm ${item.bar}`} />{item.label}</span>)}</div></CardContent></Card>;
}
function TrendPart({ count, total, color }: { count: number; total: number; color: string }) { return count ? <span className={color} style={{ height: `${(count / total) * 100}%` }} /> : null; }
function Ranking({ title, description, icon, rows, empty }: { title: string; description: string; icon: React.ReactNode; rows: Array<{ name: string; primary: string; secondary: string }>; empty: string }) { return <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base">{icon}{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader><CardContent>{rows.length ? <div className="divide-y">{rows.map((row, index) => <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0" key={row.name}><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-muted-foreground">{index + 1}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{row.name}</p><p className="mt-0.5 truncate text-xs text-muted-foreground">{row.secondary}</p></div><span className="shrink-0 text-sm font-semibold">{row.primary}</span></div>)}</div> : <EmptyText>{empty}</EmptyText>}</CardContent></Card>; }
function EmptyText({ children }: { children: React.ReactNode }) { return <p className="py-8 text-center text-sm text-muted-foreground">{children}</p>; }
