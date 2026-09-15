import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { SessionProvider } from "@/components/session-provider";
import "./globals.css";

export const metadata: Metadata = { title: "Current", description: "校园报刊投稿平台" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="zh-CN"><body><SessionProvider><AppShell>{children}</AppShell></SessionProvider></body></html>; }
