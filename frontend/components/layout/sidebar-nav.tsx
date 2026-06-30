"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clock3,
  FileText,
  Keyboard,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { cn } from "../../lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Documents", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarNavProps {
  documentId?: string;
}

export function SidebarNav({ documentId }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[rgba(8,10,18,0.98)]">
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/40">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Sentinel
          </p>
          <p className="text-[11px] text-[var(--muted-foreground)]">Review workbench</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-2.5 py-2 text-[12px] transition",
                active
                  ? "bg-sky-500/10 text-sky-100 ring-1 ring-sky-500/30"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-slate-100",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </Link>
          );
        })}

        {documentId && (
          <>
            <div className="px-2.5 pt-3 text-[10px] uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              Current document
            </div>
            <Link
              href={`/document/${documentId}`}
              className={cn(
                "flex items-center gap-2 rounded-md px-2.5 py-2 text-[12px] transition",
                pathname === `/document/${documentId}`
                  ? "bg-sky-500/10 text-sky-100 ring-1 ring-sky-500/30"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-slate-100",
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Review workspace</span>
            </Link>
            <Link
              href={`/history/${documentId}`}
              className={cn(
                "flex items-center gap-2 rounded-md px-2.5 py-2 text-[12px] transition",
                pathname === `/history/${documentId}`
                  ? "bg-sky-500/10 text-sky-100 ring-1 ring-sky-500/30"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-slate-100",
              )}
            >
              <Clock3 className="h-3.5 w-3.5" />
              <span>Audit history</span>
            </Link>
          </>
        )}
      </nav>

      <div className="border-t border-[var(--border-subtle)] px-3 py-3">
        <div className="flex items-center gap-2 text-[10px] text-[var(--muted-foreground)]">
          <Keyboard className="h-3.5 w-3.5" />
          <span>↑↓ queue · Enter approve · Del reject</span>
        </div>
      </div>
    </aside>
  );
}
