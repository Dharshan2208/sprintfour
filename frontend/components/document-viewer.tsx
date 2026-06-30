import { Detection } from "../lib/types";
import { documentParagraphs } from "../lib/mock-data";
import { cn } from "../lib/utils";

interface DocumentViewerProps {
  detections: Detection[];
  activeId: string | null;
  onSelect: (d: Detection) => void;
}

export function DocumentViewer({
  detections,
  activeId,
  onSelect,
}: DocumentViewerProps) {
  const byParagraph = detections.reduce<Record<number, Detection[]>>(
    (acc, d) => {
      if (!acc[d.paragraphIndex]) acc[d.paragraphIndex] = [];
      acc[d.paragraphIndex].push(d);
      return acc;
    },
    {},
  );

  Object.values(byParagraph).forEach((arr) => arr.sort((a, b) => a.start - b.start));

  return (
    <section
      aria-label="Document"
      className="flex h-full flex-col rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)]"
    >
      <header className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-2.5">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Document
          </span>
          <span className="text-xs text-[var(--muted-foreground)]">
            Inline AI redactions · human attention on uncertainty
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[var(--muted-foreground)]">
          <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono">
            F · Focus mode
          </span>
        </div>
      </header>

      <div className="scrollbar-thin relative flex-1 overflow-auto px-6 py-4 text-sm leading-relaxed">
        {documentParagraphs.map((paragraph, index) => (
          <p key={index} className="mb-4 text-[13px] text-slate-100/90">
            {renderParagraph(paragraph, byParagraph[index] ?? [], {
              activeId,
              onSelect,
            })}
          </p>
        ))}
      </div>
    </section>
  );
}

function renderParagraph(
  text: string,
  detections: Detection[],
  {
    activeId,
    onSelect,
  }: {
    activeId: string | null;
    onSelect: (d: Detection) => void;
  },
) {
  if (!detections.length) return text;

  const parts: React.ReactNode[] = [];
  let cursor = 0;

  for (const d of detections) {
    if (d.start > cursor) {
      parts.push(text.slice(cursor, d.start));
    }

    const spanText = text.slice(d.start, d.end);
    parts.push(
      <button
        key={d.id}
        type="button"
        onClick={() => onSelect(d)}
        className={cn(
          "relative whitespace-pre-wrap rounded-[3px] px-0.5 py-0.5 text-left underline-offset-2 transition",
          highlightClasses(d),
          activeId === d.id && "ring-1 ring-sky-400/80 ring-offset-1 ring-offset-sky-900/40",
        )}
      >
        <span className="relative z-10">{spanText}</span>
      </button>,
    );
    cursor = d.end;
  }

  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }

  return parts;
}

function highlightClasses(d: Detection) {
  if (d.status === "rejected") {
    return "bg-slate-800/40 text-slate-300/70 line-through";
  }

  if (d.status === "missed") {
    return "border-b border-dashed border-sky-400/80 bg-sky-500/5";
  }

  if (d.status === "approved") {
    return "bg-emerald-500/10 text-emerald-100";
  }

  if (d.severity === "critical") {
    return d.confidence >= 0.85
      ? "bg-red-500/80 text-red-50 shadow-[0_0_0_1px_rgba(248,113,113,0.7)]"
      : "bg-red-500/40 text-red-50/90";
  }

  if (d.severity === "high") {
    return d.confidence >= 0.8
      ? "bg-rose-500/70 text-rose-50"
      : "bg-rose-500/40 text-rose-50/90";
  }

  if (d.severity === "medium") {
    return "bg-amber-500/30 text-amber-50/90";
  }

  return "bg-sky-500/20 text-sky-50/90 underline decoration-sky-400/70";
}

