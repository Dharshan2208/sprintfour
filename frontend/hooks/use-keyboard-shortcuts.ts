import { useEffect } from "react";

interface Options {
  onPrimaryAction?: () => void;
  onReject?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  onToggleDetails?: () => void;
  onCloseSurface?: () => void;
}

export function useKeyboardShortcuts({
  onPrimaryAction,
  onReject,
  onNext,
  onPrevious,
  onToggleDetails,
  onCloseSurface,
}: Options) {
  useEffect(() => {
    const isTypingInField = (target: EventTarget | null) => {
      if (!target || !(target instanceof HTMLElement)) return false;
      const tagName = target.tagName;
      return (
        tagName === "INPUT" ||
        tagName === "TEXTAREA" ||
        target.isContentEditable
      );
    };

    function handler(e: KeyboardEvent) {
      if (isTypingInField(e.target)) return;

      switch (e.key) {
        case "ArrowDown":
          onNext?.();
          e.preventDefault();
          break;
        case "ArrowUp":
          onPrevious?.();
          e.preventDefault();
          break;
        case "Enter":
          onPrimaryAction?.();
          e.preventDefault();
          break;
        case "Backspace":
        case "Delete":
          onReject?.();
          e.preventDefault();
          break;
        case " ":
          onToggleDetails?.();
          e.preventDefault();
          break;
        case "Escape":
          onCloseSurface?.();
          break;
        case "tab":
          onNext?.();
          e.preventDefault();
          break;
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onPrimaryAction, onReject, onNext, onPrevious, onToggleDetails, onCloseSurface]);
}

