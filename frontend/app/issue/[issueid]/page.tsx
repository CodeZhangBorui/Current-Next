"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Check, Download, Eye, FileCheck, Trash2, Upload } from "lucide-react";
import { api } from "@/lib/api";
import type { Entry, Issue } from "@/lib/types";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

export default function IssuePage() {
  const params = useParams<{ issueid: string }>(); const [issue, setIssue] = useState<Issue | null>(null); const [entries, setEntries] = useState<Entry[]>([]);
  const load = () => api.get(`/issues/${params.issueid}`).then(({ data }) => { setIssue(data.issue); setEntries(data.entries); });
  useEffect(() => { load(); }, [params.issueid]);
  if (!issue) return <p className="text-muted-foreground">正在加载...</p>;
  return <div className="space-y-6"><div><Link className="text-sm text-muted-foreground hover:text-foreground" href="/">返回期刊列表</Link><div className="mt-3 flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm text-muted-foreground">Current</p><h1 className="text-3xl font-bold">第 {issue.id} 期</h1></div>{issue.published ? <a href={`${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/issues/${issue.id}/pdf`} target="_blank"><Button variant="outline"><Eye className="mr-2 h-4 w-4" />查看 PDF</Button></a> : <Link href={`/issue/${issue.id}/newentry`}><Button><Upload className="mr-2 h-4 w-4" />新建投稿</Button></Link>}</div></div>{[1, 2, 3, 4].map((page) => <section key={page}><h2 className="mb-3 text-lg font-semibold">第 {page} 版{page > 1 && <span className="ml-2 font-normal text-muted-foreground">{issue.subject[page - 2]}</span>}</h2><div className="space-y-3">{entries.filter((entry) => entry.page === page).map((entry) => <EntryCard entry={entry} key={entry.uuid} reload={load} />)}{entries.filter((entry) => entry.page === page).length === 0 && <Card><CardContent className="p-5 text-sm text-muted-foreground">暂无文章</CardContent></Card>}</div></section>)}</div>;
}

function EntryCard({ entry, reload }: { entry: Entry; reload: () => void }) {
  const review = async (file: File) => { const form = new FormData(); form.append("file", file); await api.post(`/entries/${entry.uuid}/review`, form, { headers: { "Content-Type": "multipart/form-data" } }); reload(); };
  const select = async () => { await api.post(`/entries/${entry.uuid}/select`); reload(); };
  const remove = async () => { if (window.confirm(`确认删除“${entry.title}”？`)) { await api.delete(`/entries/${entry.uuid}`); reload(); } };
  return <Card><CardHeader className="flex-row items-center justify-between"><CardTitle className="flex items-center gap-2 text-base">{entry.status === "selected" || entry.status === "reviewed" ? <Check className="h-5 w-5 text-green-600" /> : <FileCheck className="h-5 w-5 text-primary" />}{entry.title}</CardTitle><span className="text-xs text-muted-foreground">{entry.status}</span></CardHeader><CardContent className="space-y-3 pt-0 text-sm"><p><b>来源：</b>{entry.origin}　<b>词数：</b>{entry.wordcount}</p><p className="text-muted-foreground">{entry.description}</p><div className="flex flex-wrap gap-2"><a href={`${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/entries/${entry.uuid}/file`} target="_blank"><Button variant="outline"><Download className="mr-2 h-4 w-4" />下载文件</Button></a>{entry.status === "created" && <label className="inline-flex h-10 cursor-pointer items-center justify-center rounded-md border border-input px-4 text-sm font-medium hover:bg-muted"><FileCheck className="mr-2 h-4 w-4" />审核<input className="hidden" type="file" accept=".doc,.docx" onChange={(e) => e.target.files?.[0] && review(e.target.files[0])} /></label>}{(entry.status === "reviewed" || entry.status === "selected") && <Button variant="outline" onClick={select}><Check className="mr-2 h-4 w-4" />{entry.status === "selected" ? "取消选录" : "选录"}</Button>}<Button variant="destructive" onClick={remove}><Trash2 className="mr-2 h-4 w-4" />删除</Button></div></CardContent></Card>;
}
