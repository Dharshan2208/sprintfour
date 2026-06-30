import { useEffect } from "react";

interface KeyboardShortcutOptions {
  enabled?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: () => void;
  onAdd?: () => void;
  onDelete?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  onNextUnresolved?: () => void;
  onPreviousUnresolved?: () => void;
  onNextOccurrence?: () => void;
  onPreviousOccurrence?: () => void;
  onToggleDetails?: () => void;
  onExport?: () => void;
  onSearch?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onCloseSurface?: () => void;
}

export function useKeyboardShortcuts({
  enabled = true,
  onApprove,
  onReject,
  onEdit,
  onAdd,
  onDelete,
  onNext,
  onPrevious,
  onNextUnresolved,
  onPreviousUnresolved,
  onNextOccurrence,
  onPreviousOccurrence,
  onToggleDetails,
  onExport,
  onSearch,
  onUndo,
  onRedo,
  onCloseSurface,
}: KeyboardShortcutOptions) {
  useEffect(() => {
    if (!enabled) return;

    const isTypingInField = (target: EventTarget | null) => {
      if (!target || !(target instanceof HTMLElement)) return false;
      const tagName = target.tagName;
      return tagName === "INPUT" || tagName === "TEXTAREA" || target.isContentEditable;
    };

    function handler(event: KeyboardEvent) {
      if (isTypingInField(event.target)) return;

      const key = event.key.toLowerCase();
      const withCtrl = event.ctrlKey || event.metaKey;

      if (withCtrl && event.shiftKey && key === "z") {
        onRedo?.();
        event.preventDefault();
        return;
      }

      if (withCtrl && key === "z") {
        onUndo?.();
        event.preventDefault();
        return;
      }

      if (withCtrl && key === "e") {
        onExport?.();
        event.preventDefault();
        return;
      }

      if (withCtrl && key === "f") {
        onSearch?.();
        event.preventDefault();
        return;
      }

      if (withCtrl && key === "g") {
        onNextOccurrence?.();
        event.preventDefault();
        return;
      }

      if (event.key === "ArrowDown") {
        onNext?.();
        event.preventDefault();
        return;
      }

      if (event.key === "ArrowUp") {
        onPrevious?.();
        event.preventDefault();
        return;
      }

      if (event.key === "ArrowRight") {
        onNextOccurrence?.();
        event.preventDefault();
        return;
      }

      if (event.key === "ArrowLeft") {
        onPreviousOccurrence?.();
        event.preventDefault();
        return;
      }

      if (event.key === "Enter") {
        onApprove?.();
        event.preventDefault();
        return;
      }

      if (event.key === "Backspace" || event.key === "Delete") {
        onReject?.();
        event.preventDefault();
        return;
      }

      if (key === "e" && !withCtrl) {
        onEdit?.();
        event.preventDefault();
        return;
      }

      if (key === "a" && !withCtrl) {
        onAdd?.();
        event.preventDefault();
        return;
      }

      if (event.key === "Tab" && event.shiftKey) {
        onPreviousUnresolved?.();
        event.preventDefault();
        return;
      }

      if (event.key === "Tab") {
        onNextUnresolved?.();
        event.preventDefault();
        return;
      }

      if (event.key === " ") {
        onToggleDetails?.();
        event.preventDefault();
        return;
      }

      if (event.key === "Escape") {
        onCloseSurface?.();
        return;
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [
    enabled,
    onAdd,
    onApprove,
    onCloseSurface,
    onDelete,
    onEdit,
    onExport,
    onNext,
    onNextOccurrence,
    onNextUnresolved,
    onPrevious,
    onPreviousOccurrence,
    onPreviousUnresolved,
    onRedo,
    onReject,
    onSearch,
    onToggleDetails,
    onUndo,
  ]);
}
