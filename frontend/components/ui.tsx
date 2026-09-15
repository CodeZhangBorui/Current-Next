import * as React from "react";
import { cn } from "@/lib/utils";

export function Button({ className, variant = "default", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" | "destructive" | "ghost" }) {
  return <button className={cn("inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50", variant === "default" && "bg-primary text-primary-foreground hover:bg-primary/90", variant === "outline" && "border border-input bg-background hover:bg-muted", variant === "destructive" && "bg-destructive text-destructive-foreground hover:bg-destructive/90", variant === "ghost" && "hover:bg-muted", className)} {...props} />;
}

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />; }
export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />; }
export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) { return <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />; }
export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) { return <div className={cn("p-6 pt-0", className)} {...props} />; }
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => <input ref={ref} className={cn("flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />);
Input.displayName = "Input";
export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => <textarea ref={ref} className={cn("flex min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />);
Textarea.displayName = "Textarea";
