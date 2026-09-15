"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CalendarDays, FilePlus2 } from "lucide-react";

import { api } from "@/lib/api";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Spinner } from "@/components/ui";

export default function NewIssuePage() {
  const router = useRouter();
  const [form, setForm] = useState({ id: "", deadline: "", subject2: "", subject3: "", subject4: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); setSubmitting(true); try { await api.post("/issues", { id: Number(form.id), deadline: new Date(form.deadline).toISOString(), subject: [form.subject2, form.subject3, form.subject4] }); router.push("/"); } catch { setError("创建失败，请确认期数未重复且当前账号拥有创建权限。"); } finally { setSubmitting(false); } };
  return <div className="mx-auto max-w-2xl space-y-6"><Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />返回工作台</Link><div><p className="text-sm font-medium text-primary">编辑工作台</p><h1 className="mt-2 text-3xl font-bold tracking-tight">创建新期刊</h1><p className="mt-2 text-sm text-muted-foreground">创建后即可开放投稿，发布前可以持续收集和审核稿件。</p></div><Card><CardHeader><CardTitle>期刊信息</CardTitle><CardDescription>请确认期数和截止日期后再创建。</CardDescription></CardHeader><CardContent><form className="space-y-5" onSubmit={submit}><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-medium">期数 *<Input className="mt-2" min="1" required type="number" value={form.id} onChange={(event) => update("id", event.target.value)} /></label><label className="block text-sm font-medium"><span className="flex items-center gap-2">截止日期 *<CalendarDays className="h-4 w-4 text-muted-foreground" /></span><Input className="mt-2" required type="datetime-local" value={form.deadline} onChange={(event) => update("deadline", event.target.value)} /></label></div>{[["subject2", "第二版主题"], ["subject3", "第三版主题"], ["subject4", "第四版主题"]].map(([field, label]) => <label className="block text-sm font-medium" key={field}>{label} *<Input className="mt-2" required value={form[field as keyof typeof form]} onChange={(event) => update(field as keyof typeof form, event.target.value)} /></label>)}{error && <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}<div className="flex justify-end gap-2 border-t pt-5"><Link href="/"><Button type="button" variant="outline">取消</Button></Link><Button disabled={submitting} type="submit">{submitting ? <Spinner className="mr-2" /> : <FilePlus2 className="mr-2 h-4 w-4" />}创建期刊</Button></div></form></CardContent></Card></div>;
}
