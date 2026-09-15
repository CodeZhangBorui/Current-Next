import { Link } from "@/components/page-transition";
import { ArrowLeft, BarChart3 } from "lucide-react";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

export default function StatisticPage() { return <div className="space-y-6"><Link className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" href="/"><ArrowLeft className="h-4 w-4" />返回工作台</Link><Card><CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5 text-primary" />统计</CardTitle></CardHeader><CardContent className="p-10 text-center"><BarChart3 className="mx-auto h-10 w-10 text-muted-foreground" /><p className="mt-4 font-medium">统计面板即将上线</p><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">当前可以在每一期的详情页查看投稿、审核和选录数量。后续将提供跨期趋势和作者维度统计。</p><Link href="/"><Button className="mt-5" variant="outline">返回期刊列表</Button></Link></CardContent></Card></div>; }
