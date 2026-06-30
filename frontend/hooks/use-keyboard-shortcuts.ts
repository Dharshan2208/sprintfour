import { useEffect } from "react";

interface Options {
  onApprove?: () => void;
  onReject?: () => void;
  onMarkMissed?: () => void;
  onNext?: () => void;
}

export function useKeyboardShortcuts({
  onApprove,
  onReject,
  onMarkMissed,
  onNext,
}: Options) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.target && (e.target as HTMLElement).tagName === "INPUT") return;
      if (e.target && (e.target as HTMLElement).tagName === "TEXTAREA") return;

      switch (e.key.toLowerCase()) {
        case "a":
          onApprove?.();
          e.preventDefault();
          break;
        case "r":
          onReject?.();
          e.preventDefault();
          break;
        case "m":
          onMarkMissed?.();
          e.preventDefault();
          break;
        case "tab":
          onNext?.();
          e.preventDefault();
          break;
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onApprove, onReject, onMarkMissed, onNext]);
}

