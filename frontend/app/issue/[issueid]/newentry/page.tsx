"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, FileUp, UploadCloud } from "lucide-react";

import { api } from "@/lib/api";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Spinner, Textarea } from "@/components/ui";

export default function NewEntryPage() {
  const params = useParams<{ issueid: string }>();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState({ page: "1", title: "", origin: "", wordcount: "", description: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (field: keyof typeof form, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (!file) return setError("请选择一份 .doc 或 .docx 文件。");
    setSubmitting(true);
    try {
      const data = new FormData();
      Object.entries(form).forEach(([key, value]) => data.append(key, value));
      data.append("file", file);
      await api.post(`/issues/${params.issueid}/entries`, data);
      router.push(`/issue/${params.issueid}`);
    } catch {
      setError("投稿提交失败。请确认期刊仍在征稿，并检查账号权限。");
    } finally { setSubmitting(false); }
  };

  return <div className="mx-auto max-w-3xl space-y-6"><Link href={`/issue/${params.issueid}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />返回第 {params.issueid} 期</Link><div><p className="text-sm font-medium text-primary">投稿工作台</p><h1 className="mt-2 text-3xl font-bold tracking-tight">提交一篇新稿</h1><p className="mt-2 text-sm text-muted-foreground">填写文章信息并上传文件，提交后可在期刊详情中查看审核状态。</p></div><div className="grid gap-6 lg:grid-cols-[1fr_280px]"><Card><CardHeader><CardTitle>稿件信息</CardTitle><CardDescription>带有 * 的字段为必填项。</CardDescription></CardHeader><CardContent><form className="space-y-5" onSubmit={submit}><label className="block text-sm font-medium">版页 *<select className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring" value={form.page} onChange={(event) => update("page", event.target.value)}>{[1, 2, 3, 4].map((page) => <option key={page} value={page}>第 {page} 版</option>)}</select></label><label className="block text-sm font-medium">文章标题 *<Input className="mt-2" placeholder="例如：校园科技节顺利闭幕" required value={form.title} onChange={(event) => update("title", event.target.value)} /></label><label className="block text-sm font-medium">文章来源 *<Input className="mt-2" placeholder="例如：校园记者站" required value={form.origin} onChange={(event) => update("origin", event.target.value)} /></label><label className="block text-sm font-medium">词数 *<Input className="mt-2" min="1" placeholder="请输入文章词数" required type="number" value={form.wordcount} onChange={(event) => update("wordcount", event.target.value)} /></label><label className="block text-sm font-medium">内容简介<Textarea className="mt-2" placeholder="用一两句话说明文章内容，帮助编辑快速了解稿件。" value={form.description} onChange={(event) => update("description", event.target.value)} /></label><div><p className="text-sm font-medium">稿件文件 *</p><label className="mt-2 flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-primary/40 bg-primary/[0.03] px-4 text-center hover:bg-primary/[0.06]"><UploadCloud className="h-7 w-7 text-primary" /><span className="mt-2 text-sm font-medium">点击选择 Word 文件</span><span className="mt-1 text-xs text-muted-foreground">支持 .doc、.docx</span><input className="hidden" required type="file" accept=".doc,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>{file && <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground"><FileUp className="h-4 w-4 text-green-600" />{file.name}</p>}</div>{error && <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}<div className="flex justify-end gap-2 border-t pt-5"><Link href={`/issue/${params.issueid}`}><Button type="button" variant="outline">取消</Button></Link><Button disabled={submitting} type="submit">{submitting && <Spinner className="mr-2" />}提交投稿</Button></div></form></CardContent></Card><Card className="h-fit"><CardHeader><CardTitle className="text-base">提交前确认</CardTitle></CardHeader><CardContent className="space-y-4 text-sm text-muted-foreground"><p className="flex gap-2"><CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />文件内容应与表单中的标题和来源一致。</p><p className="flex gap-2"><CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />提交后稿件会进入待审核状态。</p><p className="flex gap-2"><CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />如需修改，请联系编辑删除后重新投稿。</p></CardContent></Card></div></div>;
}
