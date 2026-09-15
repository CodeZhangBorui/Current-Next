"use client";

import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useRef } from "react";

type NavigationOptions = { scroll?: boolean };
type TransitionContextValue = {
  navigate: (href: string, method?: "push" | "replace", options?: NavigationOptions) => Promise<void>;
};

const TransitionContext = createContext<TransitionContextValue | null>(null);

function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function PageTransitionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const navigating = useRef(false);
  const initialRender = useRef(true);

  useLayoutEffect(() => {
    const page = document.querySelector<HTMLElement>(".app-page");
    if (!page) return;
    page.getAnimations().forEach((animation) => animation.cancel());
    navigating.current = false;
    if (initialRender.current) {
      initialRender.current = false;
      return;
    }
    const duration = reducedMotion() ? 100 : 210;
    page.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration, easing: "cubic-bezier(0.1, 0.9, 0.2, 1)", fill: "both" },
    );
  }, [pathname]);

  const navigate = useCallback(async (href: string, method: "push" | "replace" = "push", options?: NavigationOptions) => {
    if (navigating.current) return;
    navigating.current = true;
    const duration = reducedMotion() ? 70 : 130;
    const page = document.querySelector<HTMLElement>(".app-page");
    if (page) {
      const exit = page.animate(
        [{ opacity: 1 }, { opacity: 0 }],
        { duration, easing: "cubic-bezier(0.7, 0, 1, 0.5)", fill: "forwards" },
      );
      await exit.finished.catch(() => undefined);
    }
    router[method](href, options);
  }, [router]);

  const value = useMemo(() => ({ navigate }), [navigate]);
  return <TransitionContext.Provider value={value}>{children}</TransitionContext.Provider>;
}

export function Link(props: React.ComponentProps<typeof NextLink>) {
  const context = useContext(TransitionContext);
  const { href, onClick, replace, scroll, target, ...rest } = props;
  return <NextLink
    {...rest}
    href={href}
    replace={replace}
    scroll={scroll}
    target={target}
    onClick={(event) => {
      onClick?.(event);
      if (event.defaultPrevented || !context || typeof href !== "string") return;
      if (target && target !== "_self") return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin || url.pathname.startsWith("/admin/") || url.pathname === "/admin") return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      event.preventDefault();
      void context.navigate(`${url.pathname}${url.search}${url.hash}`, replace ? "replace" : "push", { scroll });
    }}
  />;
}

export function useTransitionRouter() {
  const router = useRouter();
  const context = useContext(TransitionContext);
  return useMemo(() => ({
    ...router,
    push: (href: string, options?: NavigationOptions) => context ? void context.navigate(href, "push", options) : router.push(href, options),
    replace: (href: string, options?: NavigationOptions) => context ? void context.navigate(href, "replace", options) : router.replace(href, options),
  }), [context, router]);
}
