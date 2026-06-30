"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Download, X } from "lucide-react";
import { useState } from "react";
import type { UserSettings } from "../../lib/types";
import { downloadJsonFile, downloadTextFile } from "../../lib/utils";

interface ExportModalProps {
  open: boolean;
  defaultFormat: UserSettings["defaultExportFormat"];
  isExporting: boolean;
  onClose: () => void;
  onExport: (format: UserSettings["defaultExportFormat"]) => Promise<{
    redacted_text?: string;
    json_report?: Record<string, unknown>;
  } | null>;
  filename: string;
}

export function ExportModal({
  open,
  defaultFormat,
  isExporting,
  onClose,
  onExport,
  filename,
}: ExportModalProps) {
  const [format, setFormat] = useState<UserSettings["defaultExportFormat"]>(defaultFormat);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center px-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
          >
            <div className="w-full max-w-md rounded-xl border border-[var(--border-subtle)] bg-[rgba(5,7,14,0.98)] p-4 shadow-2xl">
              <header className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-200">
                    Export options
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">TXT, PDF text, or JSON report</p>
                </div>
                <button type="button" onClick={onClose} className="rounded-md border border-[var(--border-subtle)] p-1">
                  <X className="h-3 w-3" />
                </button>
              </header>

              <div className="space-y-2">
                {(["txt", "pdf", "json"] as const).map((option) => (
                  <label
                    key={option}
                    className="flex cursor-pointer items-center gap-2 rounded-md border border-[var(--border-subtle)] px-3 py-2 text-[12px]"
                  >
                    <input
                      type="radio"
                      name="export-format"
                      checked={format === option}
                      onChange={() => setFormat(option)}
                    />
                    <span className="uppercase">{option}</span>
                  </label>
                ))}
              </div>

              <footer className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-[var(--border-subtle)] px-3 py-1.5 text-[10px]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isExporting}
                  onClick={async () => {
                    const result = await onExport(format);
                    if (!result) return;
                    const base = filename.replace(/\.[^.]+$/, "");
                    if (format === "json") {
                      downloadJsonFile(`${base}-report.json`, result.json_report ?? {});
                    } else {
                      downloadTextFile(
                        `${base}-redacted.${format === "pdf" ? "txt" : "txt"}`,
                        result.redacted_text ?? "",
                      );
                    }
                    onClose();
                  }}
                  className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/70 bg-emerald-500/20 px-3 py-1.5 text-[10px] font-medium text-emerald-50 disabled:opacity-40"
                >
                  <Download className="h-3.5 w-3.5" />
                  {isExporting ? "Exporting…" : "Download export"}
                </button>
              </footer>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
