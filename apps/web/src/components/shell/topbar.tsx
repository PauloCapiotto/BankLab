"use client";

import { LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearSession, getUser } from "@/lib/session";

export function Topbar({ unreadCount }: { unreadCount: number }) {
  const router = useRouter();
  const user = getUser();

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  return (
    <header className="flex items-center justify-between border-b border-border-warm bg-surface px-8 py-4">
      <p className="text-sm text-muted">
        Olá, <span className="font-medium text-ink">{user?.name}</span>
      </p>
      <div className="flex items-center gap-4">
        <Link
          href="/notificacoes"
          className="rounded-full bg-surface-warm px-4 py-1.5 text-sm font-medium text-ink hover:bg-border-warm"
        >
          Notificações
          {unreadCount > 0 && (
            <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-xs text-white">
              {unreadCount}
            </span>
          )}
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-muted hover:text-ink"
        >
          <LogOut size={16} aria-hidden />
          Sair
        </button>
      </div>
    </header>
  );
}
