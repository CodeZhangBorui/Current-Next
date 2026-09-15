"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "@/components/page-transition";
import { ArrowLeft, CheckCircle2, Clock3, Eye, KeyRound, Megaphone, Save, Send, UserRound } from "lucide-react";
import { api } from "@/lib/api";
import type { AnnouncementManager } from "@/lib/types";
import { useSession } from "@/components/session-provider";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Spinner, Textarea } from "@/components/ui";

function formatPublishTime(value: string) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "尚未发布";
}

export default function SettingsPage() {
  const { user, logout } = useSession();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [announcement, setAnnouncement] = useState<AnnouncementManager | null>(null);
  const [content, setContent] = useState("");
  const [announcementError, setAnnouncementError] = useState("");
  const [announcementMessage, setAnnouncementMessage] = useState("");
  const [loadingAnnouncement, setLoadingAnnouncement] = useState(false);
  const [savingAnnouncement, setSavingAnnouncement] = useState<"save" | "publish" | null>(null);

  useEffect(() => {
    if (!user?.is_staff) return;
    setLoadingAnnouncement(true);
    api.get<AnnouncementManager>("/announcement/manage")
      .then(({ data }) => { setAnnouncement(data); setContent(data.draft); })
      .catch(() => setAnnouncementError("公告信息加载失败，请刷新后重试。"))
      .finally(() => setLoadingAnnouncement(false));
  }, [user?.is_staff]);

  const dirty = useMemo(() => announcement !== null && content !== announcement.draft, [announcement, content]);
  const submitPassword = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api.post("/auth/password", { old_password: oldPassword, new_password: newPassword });
      setMessage("密码修改成功，请重新登录。");
      setTimeout(logout, 800);
    } catch {
      setMessage("密码修改失败，请检查原密码。");
    }
  };
  const updateAnnouncement = async (action: "save" | "publish") => {
    setAnnouncementError("");
    setAnnouncementMessage("");
    setSavingAnnouncement(action);
    try {
      const { data } = await api.post("/announcement/manage", { action, content });
      setAnnouncement((current) => ({
        draft: content,
        published: action === "publish" ? content : current?.published || "",
        published_at: action === "publish" ? data.published_at : current?.published_at || "",
        published_by: action === "publish" ? data.published_by : current?.published_by || "",
      }));
      setAnnouncementMessage(action === "publish" ? "已发布，工作台将立即显示最新公告。" : "草稿已保存，尚未对用户发布。");
    } catch {
      setAnnouncementError(action === "publish" ? "发布失败，请稍后重试。" : "草稿保存失败，请稍后重试。");
    } finally {
      setSavingAnnouncement(null);
    }
  };

  return <div className="mx-auto max-w-5xl space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" href="/"><ArrowLeft className="h-4 w-4" />返回工作台</Link>
    <div><p className="text-sm font-medium text-primary">账户与站点</p><h1 className="mt-2 text-3xl font-bold">个人设置</h1><p className="mt-2 text-sm text-muted-foreground">管理个人资料；管理员还可以编辑并发布工作台公告。</p></div>
    <section className="grid gap-4 lg:grid-cols-2">
      <Card><CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="h-5 w-5 text-primary" />个人信息</CardTitle></CardHeader><CardContent className="grid gap-4 text-sm sm:grid-cols-3 lg:grid-cols-1"><InfoItem label="姓名" value={user?.username || "-"} /><InfoItem label="年级" value={user?.grade ? `${user.grade} 年级` : "未设置"} /><InfoItem label="班级" value={user?.classnum ? `${user.classnum} 班` : "未设置"} /></CardContent></Card>
      <Card><CardHeader><CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary" />修改密码</CardTitle></CardHeader><CardContent><form className="space-y-4" onSubmit={submitPassword}><Input type="password" placeholder="原密码" value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} required /><Input type="password" placeholder="新密码（至少 8 位）" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} /><Button type="submit">确认修改</Button>{message && <p className="text-sm text-muted-foreground">{message}</p>}</form></CardContent></Card>
    </section>
    {user?.is_staff && <Card>
      <CardHeader className="border-b"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><CardTitle className="flex items-center gap-2"><Megaphone className="h-5 w-5 text-primary" />站点公告</CardTitle><CardDescription className="mt-2">先保存草稿，再在确认预览后发布到所有用户的工作台。</CardDescription></div><div className="flex items-center gap-2 text-sm text-muted-foreground"><Clock3 className="h-4 w-4" />{announcement ? formatPublishTime(announcement.published_at) : "正在加载"}</div></div></CardHeader>
      <CardContent className="p-0">{loadingAnnouncement ? <div className="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground"><Spinner />正在加载公告...</div> : <div className="grid lg:grid-cols-2"><div className="space-y-4 p-6"><label className="block text-sm font-medium" htmlFor="announcement-content">公告内容</label><Textarea id="announcement-content" className="min-h-64 resize-y leading-6" maxLength={4000} placeholder="例如：本期征稿将于周五 18:00 截止，请及时提交审核稿。" value={content} onChange={(event) => setContent(event.target.value)} /><div className="flex items-center justify-between text-xs text-muted-foreground"><span>{dirty ? "有未保存的修改" : "草稿已保存"}</span><span>{content.length}/4000</span></div><div className="flex flex-wrap justify-end gap-2 border-t pt-4"><Button type="button" variant="outline" disabled={savingAnnouncement !== null || !dirty} onClick={() => updateAnnouncement("save")}>{savingAnnouncement === "save" ? <Spinner className="mr-2" /> : <Save className="mr-2 h-4 w-4" />}保存草稿</Button><Button type="button" disabled={savingAnnouncement !== null} onClick={() => updateAnnouncement("publish")}>{savingAnnouncement === "publish" ? <Spinner className="mr-2" /> : <Send className="mr-2 h-4 w-4" />}发布公告</Button></div>{announcementError && <p className="text-sm text-destructive">{announcementError}</p>}{announcementMessage && <p className="flex items-center gap-2 text-sm text-green-700"><CheckCircle2 className="h-4 w-4" />{announcementMessage}</p>}</div><div className="border-t bg-muted/30 p-6 lg:border-l lg:border-t-0"><p className="flex items-center gap-2 text-sm font-medium"><Eye className="h-4 w-4 text-primary" />工作台预览</p><div className="mt-4 border-l-2 border-primary/40 pl-4"><p className="text-sm font-semibold">站点公告</p><p className="mt-2 min-h-24 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{content || "公告内容将在这里显示。"}</p></div><div className="mt-6 border-t pt-4 text-xs text-muted-foreground"><p>当前已发布：{announcement?.published ? "有" : "暂无"}</p>{announcement?.published_by && <p className="mt-1">发布人：{announcement.published_by}</p>}</div></div></div>}</CardContent>
    </Card>}
  </div>;
}

function InfoItem({ label, value }: { label: string; value: string }) { return <div><p className="text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div>; }
