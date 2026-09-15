"use client";

import { FormEvent, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Textarea } from "@/components/ui";

export default function NewEntryPage() {
  const params = useParams<{ issueid: string }>(); const router = useRouter(); const [file, setFile] = useState<File | null>(null); const [form, setForm] = useState({ page: "1", title: "", origin: "", wordcount: "", description: "" }); const [error, setError] = useState("");
  const submit = async (event: FormEvent) => { event.preventDefault(); if (!file) return setError("请选择稿件文件。"); try { const data = new FormData(); Object.entries(form).forEach(([key, value]) => data.append(key, value)); data.append("file", file); await api.post(`/issues/${params.issueid}/entries`, data, { headers: { "Content-Type": "multipart/form-data" } }); router.push(`/issue/${params.issueid}`); } catch { setError("提交失败，请检查内容后重试。"); } };
  return <div className="mx-auto max-w-2xl space-y-5"><Link href={`/issue/${params.issueid}`} className="text-sm text-muted-foreground">返回期刊</Link><Card><CardHeader><CardTitle>新建投稿</CardTitle></CardHeader><CardContent><form className="space-y-4" onSubmit={submit}><label className="block text-sm">版页<select className="mt-2 flex h-10 w-full rounded-md border bg-background px-3" value={form.page} onChange={(e) => setForm({ ...form, page: e.target.value })}>{[1, 2, 3, 4].map((page) => <option key={page} value={page}>第 {page} 版</option>)}</select></label><label className="block text-sm">标题<Input className="mt-2" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label><label className="block text-sm">来源<Input className="mt-2" required value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })} /></label><label className="block text-sm">词数<Input className="mt-2" required min="1" type="number" value={form.wordcount} onChange={(e) => setForm({ ...form, wordcount: e.target.value })} /></label><label className="block text-sm">描述<Textarea className="mt-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label><label className="block text-sm">稿件文件<input className="mt-2 block w-full text-sm" required type="file" accept=".doc,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>{error && <p className="text-sm text-destructive">{error}</p>}<Button type="submit">提交投稿</Button></form></CardContent></Card></div>;
}
