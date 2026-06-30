"use client";

import { Search } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  inputRef?: React.RefObject<HTMLInputElement | null>;
}

export function SearchBar({ value, onChange, inputRef }: SearchBarProps) {
  return (
    <label className="flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--muted)]/70 px-2 py-1.5 text-[11px] text-[var(--muted-foreground)]">
      <Search className="h-3.5 w-3.5" />
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search entity, type, status, page…"
        className="w-full bg-transparent outline-none placeholder:text-[var(--muted-foreground)]"
      />
      <kbd className="rounded bg-black/40 px-1 py-0.5 font-mono text-[9px]">⌘F</kbd>
    </label>
  );
}
