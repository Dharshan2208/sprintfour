"use client";

import type { DocumentPage } from "../../lib/types";
import { cn } from "../../lib/utils";

interface DocumentNavigatorProps {
  pages: DocumentPage[];
  selectedPage: number | null;
  onSelectPage: (page: number | null) => void;
}

export function DocumentNavigator({
  pages,
  selectedPage,
  onSelectPage,
}: DocumentNavigatorProps) {
  if (pages.length <= 1) return null;

  return (
    <div className="flex flex-wrap gap-1 border-b border-[var(--border-subtle)] px-3 py-2">
      <button
        type="button"
        onClick={() => onSelectPage(null)}
        className={cn(
          "rounded-md px-2 py-1 text-[10px]",
          selectedPage === null
            ? "bg-sky-500/10 text-sky-100 ring-1 ring-sky-500/30"
            : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
        )}
      >
        All pages
      </button>
      {pages.map((page) => (
        <button
          key={page.page_number}
          type="button"
          onClick={() => onSelectPage(page.page_number)}
          className={cn(
            "rounded-md px-2 py-1 font-mono text-[10px]",
            selectedPage === page.page_number
              ? "bg-sky-500/10 text-sky-100 ring-1 ring-sky-500/30"
              : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
          )}
        >
          P{page.page_number}
        </button>
      ))}
    </div>
  );
}
