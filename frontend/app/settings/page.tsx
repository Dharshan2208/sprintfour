"use client";

import { AppLayout } from "../../components/layout/app-layout";
import { useUIStore } from "../../stores/ui-store";

export default function SettingsPage() {
  const settings = useUIStore((state) => state.settings);
  const updateSettings = useUIStore((state) => state.updateSettings);

  return (
    <AppLayout>
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
        <header>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
            Settings
          </p>
          <h1 className="mt-1 text-xl font-medium text-slate-50">Reviewer preferences</h1>
        </header>

        <section className="space-y-4 rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)] p-4">
          <Field label="Actor name" hint="Sent to review and export APIs">
            <input
              value={settings.actorName}
              onChange={(event) => updateSettings({ actorName: event.target.value })}
              className="w-full rounded-md border border-[var(--border-subtle)] bg-black/20 px-3 py-2 text-sm outline-none"
            />
          </Field>

          <Field label="Default export format">
            <select
              value={settings.defaultExportFormat}
              onChange={(event) =>
                updateSettings({
                  defaultExportFormat: event.target.value as typeof settings.defaultExportFormat,
                })
              }
              className="w-full rounded-md border border-[var(--border-subtle)] bg-black/20 px-3 py-2 text-sm outline-none"
            >
              <option value="txt">TXT</option>
              <option value="pdf">PDF</option>
              <option value="json">JSON report</option>
            </select>
          </Field>

          <label className="flex items-center justify-between gap-3 text-sm text-slate-100">
            <span>
              Require full review before export
              <p className="text-[12px] text-[var(--muted-foreground)]">
                Passes <code>require_full_review</code> to validation API.
              </p>
            </span>
            <input
              type="checkbox"
              checked={settings.requireFullReview}
              onChange={(event) => updateSettings({ requireFullReview: event.target.checked })}
            />
          </label>

          <label className="flex items-center justify-between gap-3 text-sm text-slate-100">
            <span>Show keyboard hints</span>
            <input
              type="checkbox"
              checked={settings.showKeyboardHints}
              onChange={(event) => updateSettings({ showKeyboardHints: event.target.checked })}
            />
          </label>
        </section>

        <section className="rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)] p-4 text-[12px] text-[var(--muted-foreground)]">
          <p className="mb-2 font-medium text-slate-200">Keyboard shortcuts</p>
          <div className="grid gap-1 sm:grid-cols-2">
            <Shortcut keys="↑ ↓" action="Navigate queue" />
            <Shortcut keys="← →" action="Previous / next occurrence" />
            <Shortcut keys="Enter" action="Approve" />
            <Shortcut keys="Delete" action="Reject" />
            <Shortcut keys="E" action="Edit / open drawer" />
            <Shortcut keys="A" action="Add detection" />
            <Shortcut keys="Tab" action="Next unresolved issue" />
            <Shortcut keys="Shift+Tab" action="Previous unresolved issue" />
            <Shortcut keys="Ctrl+Z" action="Undo" />
            <Shortcut keys="Ctrl+Shift+Z" action="Redo" />
            <Shortcut keys="Ctrl+E" action="Export" />
            <Shortcut keys="Ctrl+F" action="Focus search" />
            <Shortcut keys="Ctrl+G" action="Next entity" />
            <Shortcut keys="Esc" action="Close panel" />
          </div>
        </section>
      </div>
    </AppLayout>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm text-slate-100">{label}</span>
      {hint && <p className="text-[12px] text-[var(--muted-foreground)]">{hint}</p>}
      {children}
    </label>
  );
}

function Shortcut({ keys, action }: { keys: string; action: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-[var(--border-subtle)] bg-black/20 px-2 py-1.5">
      <span>{action}</span>
      <kbd className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[10px] text-slate-200">
        {keys}
      </kbd>
    </div>
  );
}
