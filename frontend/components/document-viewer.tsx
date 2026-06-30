import { useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const paragraphRefs = useRef<Record<number, HTMLParagraphElement | null>>({});
  const activeDetection = useMemo(
    () => detections.find((d) => d.id === activeId) ?? null,
    [detections, activeId],
  );

  useEffect(() => {
    if (!activeDetection) return;
    const target = paragraphRefs.current[activeDetection.paragraphIndex];
    if (!target) return;

    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeDetection]);

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
          <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono text-[9px]">
            Context focus
          </span>
        </div>
      </header>

      <div
        ref={containerRef}
        className="scrollbar-thin relative flex-1 overflow-auto px-8 py-6 text-sm leading-relaxed"
      >
        {documentParagraphs.map((paragraph, index) => (
          <motion.p
            key={index}
            ref={(el) => {
              paragraphRefs.current[index] = el;
            }}
            animate={{
              opacity:
                activeDetection == null
                  ? 1
                  : activeDetection.paragraphIndex === index
                    ? 1
                    : 0.42,
              filter:
                activeDetection == null || activeDetection.paragraphIndex === index
                  ? "blur(0px)"
                  : "blur(0.4px)",
            }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className={cn(
              "mb-6 max-w-3xl text-[14px] leading-7 tracking-[0.003em] text-slate-100/90",
              activeDetection?.paragraphIndex === index &&
                "rounded-lg bg-sky-500/5 px-3 py-2 ring-1 ring-sky-500/30",
            )}
          >
            {renderParagraph(paragraph, byParagraph[index] ?? [], {
              activeId,
              onSelect,
            })}
          </motion.p>
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
    return "bg-slate-800/30 text-slate-400/60 line-through";
  }

  if (d.status === "missed") {
    return "rounded border border-sky-400/90 bg-sky-500/12 text-sky-50 shadow-[0_0_0_1px_rgba(56,189,248,0.4)]";
  }

  if (d.status === "approved") {
    return "bg-red-500/12 text-red-50/70";
  }

  if (d.severity === "critical") {
    return "bg-red-500/28 text-red-100";
  }

  if (d.severity === "high") {
    return "bg-red-500/18 text-red-100/90";
  }

  if (d.severity === "medium") {
    return "border-b border-dotted border-amber-400/80 bg-amber-500/14 text-amber-100";
  }

  return "border-b border-dotted border-amber-400/80 bg-amber-500/10 text-amber-100/85";
}

