"use client";

import { SidebarNav } from "./sidebar-nav";
import { StatusBar } from "./status-bar";
import type { ReviewStats } from "../../lib/types";

interface AppLayoutProps {
  children: React.ReactNode;
  documentId?: string;
  statusBar?: {
    filename?: string;
    stats: ReviewStats;
    riskScore?: number;
    exportReady?: boolean;
    isMutating?: boolean;
  };
}

export function AppLayout({ children, documentId, statusBar }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--background)]">
      <div className="flex min-h-0 flex-1">
        <SidebarNav documentId={documentId} />
        <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
      {statusBar && <StatusBar {...statusBar} />}
    </div>
  );
}
