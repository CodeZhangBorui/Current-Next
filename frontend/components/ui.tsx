import * as React from "react";
import { cn } from "@/lib/utils";

export function Button({ className, variant = "default", size = "default", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" | "destructive" | "ghost"; size?: "default" | "sm" | "icon" }) {
  return <button className={cn("inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50", size === "default" && "h-10 px-4 text-sm", size === "sm" && "h-9 px-3 text-sm", size === "icon" && "h-10 w-10", variant === "default" && "bg-primary text-primary-foreground hover:bg-primary/90", variant === "outline" && "border border-input bg-background hover:bg-muted", variant === "destructive" && "bg-destructive text-destructive-foreground hover:bg-destructive/90", variant === "ghost" && "hover:bg-muted", className)} {...props} />;
}

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("rounded-lg border bg-card text-card-foreground shadow-sm motion-card", className)} {...props} />; }
export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />; }
export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) { return <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />; }
export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) { return <p className={cn("text-sm text-muted-foreground", className)} {...props} />; }
export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("p-6 pt-0", className)} {...props} />; }
export function Badge({ className, variant = "default", ...props }: React.HTMLAttributes<HTMLSpanElement> & { variant?: "default" | "success" | "warning" | "muted" }) { return <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium", variant === "default" && "bg-primary/10 text-primary", variant === "success" && "bg-green-100 text-green-700", variant === "warning" && "bg-amber-100 text-amber-700", variant === "muted" && "bg-muted text-muted-foreground", className)} {...props} />; }
export function Spinner({ className }: { className?: string }) { return <span aria-label="加载中" className={cn("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)} />; }
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => <input ref={ref} className={cn("flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-shadow placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />);
Input.displayName = "Input";
export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => <textarea ref={ref} className={cn("flex min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-shadow placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />);
Textarea.displayName = "Textarea";
