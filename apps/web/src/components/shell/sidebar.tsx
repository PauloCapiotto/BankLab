"use client";

import {
  ArrowLeftRight,
  Home,
  Inbox,
  PiggyBank,
  ReceiptText,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/inicio", label: "Início", icon: Home },
  { href: "/contas", label: "Contas", icon: Wallet },
  { href: "/depositos/novo", label: "Depósitos", icon: PiggyBank },
  { href: "/transferencias/nova", label: "Transferências", icon: ArrowLeftRight },
  { href: "/extrato", label: "Extrato", icon: ReceiptText },
  { href: "/notificacoes", label: "Notificações", icon: Inbox },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border-warm bg-surface p-4">
      <p className="mb-6 px-3 font-display text-2xl font-bold text-primary">
        BankLab
      </p>
      <nav aria-label="Menu principal" className="flex flex-col gap-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                active
                  ? "bg-primary text-white"
                  : "text-ink hover:bg-surface-warm"
              }`}
            >
              <Icon size={18} aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
