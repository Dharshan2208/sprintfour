"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Undo2 } from "lucide-react";

interface UndoSnackbarProps {
  message: string | null;
  onUndo?: () => void;
  onDismiss: () => void;
}

export function UndoSnackbar({ message, onUndo, onDismiss }: UndoSnackbarProps) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          className="fixed bottom-12 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[rgba(8,10,18,0.98)] px-4 py-2 text-[11px] text-slate-100 shadow-xl"
        >
          <span>{message}</span>
          {onUndo && (
            <button
              type="button"
              onClick={onUndo}
              className="inline-flex items-center gap-1 rounded-md border border-sky-500/40 bg-sky-500/10 px-2 py-1 text-[10px] text-sky-100"
            >
              <Undo2 className="h-3 w-3" />
              Undo
            </button>
          )}
          <button type="button" onClick={onDismiss} className="text-[var(--muted-foreground)]">
            Dismiss
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
