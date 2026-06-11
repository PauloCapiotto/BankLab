"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Summary } from "@/lib/types";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router, pathname]);

  useEffect(() => {
    if (!ready) return;
    apiFetch<Summary>("/summary")
      .then((summary) => setUnreadCount(summary.unread_notifications))
      .catch(() => setUnreadCount(0));
  }, [ready, pathname]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted">
        Carregando...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar unreadCount={unreadCount} />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
