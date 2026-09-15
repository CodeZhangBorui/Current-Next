"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AlertCircle, ArrowLeft, Check, CheckCircle2, Download, Eye, FileCheck, FileText, RefreshCw, Trash2, Upload } from "lucide-react";

import { api } from "@/lib/api";
import type { Entry, Issue } from "@/lib/types";
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Spinner } from "@/components/ui";

const statusLabel: Record<Entry["status"], string> = { pending: "待投稿", created: "待审核", reviewed: "已审核", selected: "已选录" };
const pageNames = ["时事新闻", "第二版", "第三版", "第四版"];

export default function IssuePage() {
  const params = useParams<{ issueid: string }>();
  const [issue, setIssue] = useState<Issue | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activePage, setActivePage] = useState(0);

  const load = async () => {
    setLoading(true);
    setError("");
    try { const { data } = await api.get(`/issues/${params.issueid}`); setIssue(data.issue); setEntries(data.entries); } catch { setError("期刊内容加载失败，请重试。"); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [params.issueid]);

  const counts = useMemo(() => ({ total: entries.length, selected: entries.filter((entry) => entry.status === "selected").length, reviewed: entries.filter((entry) => entry.status === "reviewed" || entry.status === "selected").length }), [entries]);
  if (loading) return <LoadingState />;
  if (error || !issue) return <Card><CardContent className="flex flex-col items-center gap-3 p-12 text-center"><AlertCircle className="h-8 w-8 text-destructive" /><p className="text-sm text-destructive">{error || "期刊不存在。"}</p><Button variant="outline" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />重试</Button></CardContent></Card>;

  return <div className="space-y-6"><Link className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" href="/"><ArrowLeft className="h-4 w-4" />返回期刊列表</Link><section className="rounded-xl border bg-card p-6 shadow-sm"><div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start"><div><div className="flex flex-wrap items-center gap-2"><Badge variant={issue.published ? "success" : "warning"}>{issue.published ? "已出版" : "征稿中"}</Badge><span className="text-sm text-muted-foreground">Issue {issue.id}</span></div><h1 className="mt-3 text-3xl font-bold tracking-tight">第 {issue.id} 期</h1><p className="mt-2 text-sm text-muted-foreground">{issue.published ? "本期已经发布，欢迎查看完整 PDF。" : `截稿日期：${new Date(issue.deadline).toLocaleDateString("zh-CN")}`}</p></div>{issue.published ? <a href={`/api/v1/issues/${issue.id}/pdf`} target="_blank"><Button variant="outline"><Eye className="mr-2 h-4 w-4" />查看 PDF</Button></a> : <Link href={`/issue/${issue.id}/newentry`}><Button><Upload className="mr-2 h-4 w-4" />新建投稿</Button></Link>}</div>{!issue.published && <div className="mt-6 grid grid-cols-3 gap-2 border-t pt-5 text-center sm:max-w-md"><Stat label="已投稿" value={counts.total} /><Stat label="已审核" value={counts.reviewed} /><Stat label="已选录" value={counts.selected} /></div>}</section><div className="flex gap-2 overflow-x-auto border-b pb-2">{[0, 1, 2, 3].map((page) => <button key={page} className={`shrink-0 rounded-md px-3 py-2 text-sm ${activePage === page ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`} onClick={() => setActivePage(page)}>第 {page + 1} 版{page > 0 && <span className="ml-1 opacity-80">· {issue.subject[page - 1]}</span>}</button>)}</div><section className="space-y-3"><div className="flex items-center justify-between"><div><h2 className="text-lg font-semibold">{pageNames[activePage]}{activePage > 0 && <span className="ml-2 font-normal text-muted-foreground">{issue.subject[activePage - 1]}</span>}</h2><p className="mt-1 text-sm text-muted-foreground">{entries.filter((entry) => entry.page === activePage + 1).length} 篇投稿</p></div></div>{entries.filter((entry) => entry.page === activePage + 1).map((entry) => <EntryCard entry={entry} key={entry.uuid} reload={load} />)}{entries.filter((entry) => entry.page === activePage + 1).length === 0 && <Card><CardContent className="p-10 text-center"><FileText className="mx-auto h-8 w-8 text-muted-foreground" /><p className="mt-3 font-medium">这一版还没有投稿</p>{!issue.published && <Link href={`/issue/${issue.id}/newentry`}><Button className="mt-4" variant="outline">提交第一篇投稿</Button></Link>}</CardContent></Card>}</section></div>;
}

function LoadingState() { return <div className="flex min-h-80 items-center justify-center gap-2 text-sm text-muted-foreground"><Spinner />正在加载期刊...</div>; }
function Stat({ label, value }: { label: string; value: number }) { return <div><p className="text-xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></div>; }

function EntryCard({ entry, reload }: { entry: Entry; reload: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const review = async (file: File) => { setBusy(true); setMessage(""); try { const form = new FormData(); form.append("file", file); await api.post(`/entries/${entry.uuid}/review`, form); await reload(); } catch { setMessage("审核文件上传失败，请重试。"); } finally { setBusy(false); } };
  const select = async () => { setBusy(true); setMessage(""); try { await api.post(`/entries/${entry.uuid}/select`); await reload(); } catch { setMessage("当前账号没有执行此操作的权限。"); } finally { setBusy(false); } };
  const remove = async () => { if (!window.confirm(`确认删除“${entry.title}”？`)) return; setBusy(true); try { await api.delete(`/entries/${entry.uuid}`); await reload(); } catch { setMessage("删除失败，当前账号可能没有权限。"); } finally { setBusy(false); } };
  return <Card><CardHeader className="flex-row items-start justify-between gap-4 pb-3"><div className="min-w-0"><CardTitle className="flex items-start gap-2 text-base"><FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><span className="break-words">{entry.title}</span></CardTitle><CardDescription className="mt-2">选稿人：{entry.selector_name || "未记录"}{entry.reviewer_name && ` · 审稿人：${entry.reviewer_name}`}</CardDescription></div><Badge variant={entry.status === "selected" ? "success" : entry.status === "created" ? "warning" : "muted"}>{statusLabel[entry.status]}</Badge></CardHeader><CardContent className="space-y-4 pt-0"><div className="grid gap-2 text-sm sm:grid-cols-2"><p><span className="text-muted-foreground">来源：</span>{entry.origin}</p><p><span className="text-muted-foreground">词数：</span>{entry.wordcount}</p></div>{entry.description && <p className="border-l-2 border-primary/30 pl-3 text-sm leading-6 text-muted-foreground">{entry.description}</p>}{message && <p className="flex items-center gap-2 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{message}</p>}<div className="flex flex-wrap gap-2 border-t pt-3"><a href={`/api/v1/entries/${entry.uuid}/file`} target="_blank"><Button size="sm" variant="outline"><Download className="mr-2 h-4 w-4" />下载稿件</Button></a>{entry.status === "created" && <label className="inline-flex h-9 cursor-pointer items-center justify-center rounded-md border border-input px-3 text-sm font-medium hover:bg-muted">{busy ? <Spinner className="mr-2" /> : <FileCheck className="mr-2 h-4 w-4" />}审核<input className="hidden" type="file" accept=".doc,.docx" disabled={busy} onChange={(event) => event.target.files?.[0] && review(event.target.files[0])} /></label>}{(entry.status === "reviewed" || entry.status === "selected") && <Button size="sm" variant="outline" disabled={busy} onClick={select}><Check className="mr-2 h-4 w-4" />{entry.status === "selected" ? "取消选录" : "选录"}</Button>}<Button size="sm" variant="ghost" disabled={busy} onClick={remove}><Trash2 className="mr-2 h-4 w-4 text-destructive" />删除</Button></div></CardContent></Card>;
}
