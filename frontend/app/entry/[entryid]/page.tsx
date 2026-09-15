"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Check, CheckCircle2, CircleX, Clock3, Download, FileText, GitMerge, GitPullRequest, MessageSquare, RotateCcw, Send, Trash2, Upload } from "lucide-react";

import { api } from "@/lib/api";
import type { EntryComment, EntryFileVersion, EntryReview, EntryStateEvent, EntryStatus } from "@/lib/types";
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Spinner, Textarea } from "@/components/ui";
import { ConfirmDialog } from "@/components/confirm-dialog";

const statusLabel: Record<EntryStatus, string> = { pending: "待投稿", created: "等待审核", reviewed: "审核完成", selected: "Closed as merged", invalid: "Closed as invalid" };
type ConfirmationAction = "review" | "close-invalid" | "close-merged" | "reopen" | "delete";

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function EntryReviewPage() {
  const params = useParams<{ entryid: string }>();
  const router = useRouter();
  const [entry, setEntry] = useState<EntryReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"comment" | "upload" | "review" | "close-invalid" | "close-merged" | "reopen" | "delete" | null>(null);
  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const [versionNote, setVersionNote] = useState("");
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [closeNote, setCloseNote] = useState("");
  const [confirmationAction, setConfirmationAction] = useState<ConfirmationAction | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<EntryReview>(`/entries/${params.entryid}/review`);
      setEntry(data);
    } catch {
      setError("稿件审阅信息加载失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }, [params.entryid]);

  useEffect(() => { load(); }, [load]);

  const timeline = useMemo(() => {
    if (!entry) return [];
    const items: Array<
      | { key: string; type: "version"; at: string; value: EntryFileVersion }
      | { key: string; type: "comment"; at: string; value: EntryComment }
      | { key: string; type: "state"; at: string; value: EntryStateEvent }
    > = [
      ...entry.versions.map((value) => ({ key: `version-${value.id}`, type: "version" as const, at: value.created_at, value })),
      ...entry.comments.map((value) => ({ key: `comment-${value.id}`, type: "comment" as const, at: value.created_at, value })),
      ...entry.state_events.map((value) => ({ key: `state-${value.id}`, type: "state" as const, at: value.created_at, value })),
    ];
    return items.sort((left, right) => new Date(left.at).getTime() - new Date(right.at).getTime());
  }, [entry]);

  const addComment = async () => {
    if (!comment.trim()) return;
    setBusy("comment");
    setError("");
    try {
      const { data } = await api.post<EntryReview>(`/entries/${params.entryid}/comments`, { body: comment });
      setEntry(data);
      setComment("");
    } catch {
      setError("留言发送失败，请确认当前账号有权限参与审阅。");
    } finally {
      setBusy(null);
    }
  };

  const uploadVersion = async () => {
    if (!versionFile) return setError("请先选择要上传的新版本文件。");
    setBusy("upload");
    setError("");
    try {
      const form = new FormData();
      form.append("file", versionFile);
      form.append("note", versionNote);
      const { data } = await api.post<EntryReview>(`/entries/${params.entryid}/versions`, form);
      setEntry(data);
      setVersionFile(null);
      setVersionNote("");
    } catch {
      setError("新版本上传失败，请检查文件和稿件状态。");
    } finally {
      setBusy(null);
    }
  };

  const completeReview = async () => {
    setBusy("review");
    setError("");
    try {
      const { data } = await api.post<EntryReview>(`/entries/${params.entryid}/complete-review`);
      setEntry(data);
    } catch {
      setError("无法完成审核，请检查稿件状态。");
    } finally {
      setBusy(null);
      setConfirmationAction(null);
    }
  };

  const closeEntry = async (disposition: "invalid" | "merged") => {
    setBusy(disposition === "merged" ? "close-merged" : "close-invalid");
    setError("");
    try {
      const { data } = await api.post<EntryReview>(`/entries/${params.entryid}/close`, { disposition, note: closeNote });
      setEntry(data);
      setCloseNote("");
    } catch {
      setError(disposition === "merged" ? "无法 Close as merged，请确认审核已经完成。" : "无法 Close as invalid，请检查当前稿件状态。");
    } finally {
      setBusy(null);
      setConfirmationAction(null);
    }
  };

  const reopenEntry = async () => {
    setBusy("reopen");
    setError("");
    try {
      const { data } = await api.post<EntryReview>(`/entries/${params.entryid}/reopen`, { note: closeNote });
      setEntry(data);
      setCloseNote("");
    } catch {
      setError("无法重新打开稿件，请检查当前账号权限和期刊状态。");
    } finally {
      setBusy(null);
      setConfirmationAction(null);
    }
  };

  const removeEntry = async () => {
    if (!entry) return;
    setBusy("delete");
    try {
      await api.delete(`/entries/${entry.uuid}`);
      router.push(`/issue/${entry.issue_id}`);
    } catch {
      setError("删除失败，请检查当前账号权限。");
      setBusy(null);
      setConfirmationAction(null);
    }
  };

  const confirmation = confirmationAction ? {
    review: { title: "完成稿件审核？", description: "确认后稿件将进入主编决策阶段，并停止接收新的审核文件版本。", confirmLabel: "完成审核", onConfirm: completeReview, variant: "default" as const },
    "close-invalid": { title: "Close as invalid？", description: "稿件会被标记为无效并关闭讨论，但文件、留言和全部历史记录都会保留，之后仍可 Reopen。", confirmLabel: "Close as invalid", onConfirm: () => closeEntry("invalid"), variant: "default" as const },
    "close-merged": { title: "Close as merged？", description: "稿件会被标记为已选取并合并，审阅流程随即关闭；全部数据会保留，之后仍可 Reopen。", confirmLabel: "Close as merged", onConfirm: () => closeEntry("merged"), variant: "default" as const },
    reopen: { title: "重新打开稿件？", description: "稿件将恢复到关闭前的审核阶段，关闭事件仍会保留在时间线中。", confirmLabel: "Reopen", onConfirm: reopenEntry, variant: "default" as const },
    delete: { title: "永久删除稿件？", description: `“${entry?.title || "此稿件"}”的文件版本、留言和事件记录都会一并删除，此操作无法撤销。`, confirmLabel: "永久删除", onConfirm: removeEntry, variant: "destructive" as const },
  }[confirmationAction] : null;

  if (loading) return <div className="flex min-h-80 items-center justify-center gap-2 text-sm text-muted-foreground"><Spinner />正在加载审阅记录...</div>;
  if (!entry) return <Card><CardContent className="flex flex-col items-center gap-3 p-12 text-center"><AlertCircle className="h-8 w-8 text-destructive" /><p className="text-sm text-destructive">{error || "稿件不存在。"}</p><Button variant="outline" onClick={load}>重试</Button></CardContent></Card>;

  return <div className="mx-auto max-w-6xl space-y-6">
    <Link href={`/issue/${entry.issue_id}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />返回第 {entry.issue_id} 期</Link>
    <header className="border-b pb-6"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge className={entry.status === "invalid" ? "bg-red-100 text-red-700" : ""} variant={entry.status === "selected" ? "success" : entry.status === "created" ? "warning" : "muted"}><GitPullRequest className="mr-1 h-3.5 w-3.5" />{statusLabel[entry.status]}</Badge><span className="text-sm text-muted-foreground">第 {entry.issue_id} 期 · 第 {entry.page} 版</span></div><h1 className="mt-3 break-words text-2xl font-bold sm:text-3xl">{entry.title}</h1><p className="mt-2 text-sm text-muted-foreground">{entry.submitter?.username || entry.selector_name || "未知投稿者"} 提交于 {formatTime(entry.created_at)}</p></div>{entry.capabilities.can_delete && <Button variant="ghost" disabled={busy !== null} onClick={() => setConfirmationAction("delete")}><Trash2 className="mr-2 h-4 w-4 text-destructive" />删除稿件</Button>}</div><div className="mt-5 grid gap-3 text-sm sm:grid-cols-3"><Meta label="来源" value={entry.origin} /><Meta label="词数" value={`${entry.wordcount} 字`} /><Meta label="当前文件" value={entry.filename || "无可用文件"} /></div>{entry.description && <p className="mt-5 max-w-3xl border-l-2 border-primary/40 pl-4 text-sm leading-6 text-muted-foreground">{entry.description}</p>}</header>
    {error && <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="h-4 w-4 shrink-0" />{error}</div>}
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <main className="space-y-5">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Clock3 className="h-5 w-5 text-primary" />审阅时间线</CardTitle><CardDescription>{entry.version_count} 个文件版本，{entry.comment_count} 条留言</CardDescription></CardHeader><CardContent>{timeline.length ? <div className="divide-y">{timeline.map((item) => <TimelineItem key={item.key} item={item} />)}</div> : <p className="py-8 text-center text-sm text-muted-foreground">暂无审阅记录</p>}</CardContent></Card>
        {entry.capabilities.can_comment ? <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><MessageSquare className="h-5 w-5 text-primary" />参与讨论</CardTitle><CardDescription>留言会进入稿件时间线，审核者、主编和投稿者都能看到。</CardDescription></CardHeader><CardContent className="space-y-3"><Textarea className="min-h-28 resize-y" maxLength={4000} placeholder="留下修改建议、说明或终审意见..." value={comment} onChange={(event) => setComment(event.target.value)} /><div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{comment.length}/4000</span><Button disabled={busy !== null || !comment.trim()} onClick={addComment}>{busy === "comment" ? <Spinner className="mr-2" /> : <Send className="mr-2 h-4 w-4" />}发送留言</Button></div></CardContent></Card> : <div className="rounded-md border border-dashed p-5 text-center text-sm text-muted-foreground">{entry.status === "selected" || entry.status === "invalid" ? "稿件已关闭；重新打开后可继续讨论。" : "当前账号可以查看审阅记录，但不能参与讨论。"}</div>}
      </main>
      <aside className="space-y-4">
        <Card><CardHeader><CardTitle className="text-base">审阅进度</CardTitle></CardHeader><CardContent className="space-y-1"><ProgressStep done label="投稿已提交" detail={entry.submitter?.username || entry.selector_name || "投稿者"} /><ProgressStep done={Boolean(entry.review_completed_at)} active={entry.status === "created"} label="审核完成" detail={entry.review_completed_by?.username || entry.reviewer_name || "等待审核者"} /><ProgressStep done={entry.status === "selected" || entry.status === "invalid"} active={entry.status === "reviewed"} danger={entry.status === "invalid"} label={entry.status === "invalid" ? "Closed as invalid" : entry.status === "selected" ? "Closed as merged" : "等待主编决策"} detail={entry.merged_by?.username || (entry.status === "invalid" ? "稿件已标记为无效" : "尚未关闭")} last /></CardContent></Card>
        {entry.capabilities.can_upload_version && <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Upload className="h-5 w-5 text-primary" />上传审核版本</CardTitle><CardDescription>新文件会成为最新版，历史版本仍可下载。</CardDescription></CardHeader><CardContent className="space-y-3"><label className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-primary/40 bg-primary/[0.03] p-3 text-center"><FileText className="h-6 w-6 text-primary" /><span className="mt-2 max-w-full break-all text-sm">{versionFile?.name || "选择 Word 文件"}</span><input className="hidden" type="file" accept=".doc,.docx" onChange={(event) => setVersionFile(event.target.files?.[0] || null)} /></label><Textarea className="min-h-20 resize-y" maxLength={500} placeholder="版本说明（可选）" value={versionNote} onChange={(event) => setVersionNote(event.target.value)} /><Button className="w-full" variant="outline" disabled={busy !== null || !versionFile} onClick={uploadVersion}>{busy === "upload" ? <Spinner className="mr-2" /> : <Upload className="mr-2 h-4 w-4" />}上传新版本</Button></CardContent></Card>}
        {entry.capabilities.can_complete_review && <Button className="w-full" disabled={busy !== null} onClick={() => setConfirmationAction("review")}><CheckCircle2 className="mr-2 h-4 w-4" />我已完成稿件审核</Button>}
        {(entry.capabilities.can_close || entry.capabilities.can_reopen) && <Card><CardHeader><CardTitle className="text-base">主编决策</CardTitle><CardDescription>关闭和重新打开都不会删除稿件数据。</CardDescription></CardHeader><CardContent className="space-y-3"><Textarea className="min-h-20 resize-y" maxLength={500} placeholder="说明原因（可选，会写入时间线）" value={closeNote} onChange={(event) => setCloseNote(event.target.value)} />{entry.capabilities.can_reopen ? <Button className="w-full" variant="outline" disabled={busy !== null} onClick={() => setConfirmationAction("reopen")}><RotateCcw className="mr-2 h-4 w-4" />Reopen</Button> : <div className="space-y-2"><Button className="w-full" variant="outline" disabled={busy !== null} onClick={() => setConfirmationAction("close-invalid")}><CircleX className="mr-2 h-4 w-4" />Close as invalid</Button>{entry.status === "reviewed" && <Button className="w-full bg-green-600 hover:bg-green-700" disabled={busy !== null} onClick={() => setConfirmationAction("close-merged")}><GitMerge className="mr-2 h-4 w-4" />Close as merged</Button>}</div>}</CardContent></Card>}
      </aside>
    </div>
    {confirmation && <ConfirmDialog open title={confirmation.title} description={confirmation.description} confirmLabel={confirmation.confirmLabel} variant={confirmation.variant} busy={busy !== null} onConfirm={confirmation.onConfirm} onOpenChange={(open) => { if (!open) setConfirmationAction(null); }} />}
  </div>;
}

type TimelineValue =
  | { type: "version"; at: string; value: EntryFileVersion }
  | { type: "comment"; at: string; value: EntryComment }
  | { type: "state"; at: string; value: EntryStateEvent };

function TimelineItem({ item }: { item: TimelineValue }) {
  if (item.type === "version") {
    const uploader = item.value.uploader?.username || item.value.uploader_name || "未知用户";
    return <div className="flex gap-3 py-5 first:pt-0 last:pb-0"><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"><FileText className="h-4 w-4" /></div><div className="min-w-0 flex-1"><div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start"><div><p className="text-sm"><span className="font-semibold">{uploader}</span> 上传了 <span className="font-medium">v{item.value.version}</span></p><p className="mt-1 break-all text-sm text-muted-foreground">{item.value.filename}</p></div><a href={item.value.download_url} target="_blank"><Button size="sm" variant="outline"><Download className="mr-2 h-4 w-4" />下载</Button></a></div>{item.value.note && <p className="mt-3 whitespace-pre-wrap border-l-2 pl-3 text-sm leading-6 text-muted-foreground">{item.value.note}</p>}<p className="mt-2 text-xs text-muted-foreground">{formatTime(item.at)}</p></div></div>;
  }
  if (item.type === "comment") {
    const author = item.value.author?.username || item.value.author_name || "未知用户";
    return <div className="flex gap-3 py-5 first:pt-0 last:pb-0"><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted"><MessageSquare className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{author}</p><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">{item.value.body}</p><p className="mt-2 text-xs text-muted-foreground">{formatTime(item.at)}</p></div></div>;
  }
  const action = item.value.action;
  const actor = item.value.actor?.username || item.value.actor_name || "系统";
  const actionText = { review_completed: "完成了稿件审核", closed_invalid: "将稿件关闭为无效", closed_merged: "选取稿件并关闭为已合并", reopened: "重新打开了稿件" }[action];
  const isInvalid = action === "closed_invalid";
  const isMerged = action === "closed_merged";
  const isReopened = action === "reopened";
  return <div className="flex gap-3 py-5 first:pt-0 last:pb-0"><div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${isInvalid ? "bg-red-100 text-red-700" : isMerged ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}`}>{isInvalid ? <CircleX className="h-4 w-4" /> : isMerged ? <GitMerge className="h-4 w-4" /> : isReopened ? <RotateCcw className="h-4 w-4" /> : <Check className="h-4 w-4" />}</div><div className="min-w-0"><p className="text-sm"><span className="font-semibold">{actor}</span> {actionText}</p>{item.value.note && <p className="mt-2 whitespace-pre-wrap break-words border-l-2 pl-3 text-sm leading-6 text-muted-foreground">{item.value.note}</p>}<p className="mt-2 text-xs text-muted-foreground">{formatTime(item.at)}</p></div></div>;
}

function ProgressStep({ label, detail, done = false, active = false, danger = false, last = false }: { label: string; detail: string; done?: boolean; active?: boolean; danger?: boolean; last?: boolean }) {
  return <div className="flex gap-3"><div className="flex flex-col items-center"><span className={`flex h-6 w-6 items-center justify-center rounded-full border ${danger ? "border-red-600 bg-red-600 text-white" : done ? "border-green-600 bg-green-600 text-white" : active ? "border-primary bg-primary text-primary-foreground" : "bg-background text-muted-foreground"}`}>{done ? (danger ? <CircleX className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />) : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span>{!last && <span className={`h-10 w-px ${done ? "bg-green-300" : "bg-border"}`} />}</div><div className="pb-5"><p className={`text-sm font-medium ${danger ? "text-red-700" : active ? "text-primary" : ""}`}>{label}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div></div>;
}

function Meta({ label, value }: { label: string; value: string }) { return <div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 break-words font-medium">{value}</p></div>; }
