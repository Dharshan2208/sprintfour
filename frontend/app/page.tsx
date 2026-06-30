"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FileUp, Loader2, ShieldAlert } from "lucide-react";
import { AppLayout } from "../components/layout/app-layout";
import {
  loadDocumentRegistry,
  upsertDocumentEntry,
} from "../lib/document-registry";
import type { DocumentListEntry } from "../lib/types";
import { uploadDocument } from "../services/documents";
import { cn } from "../lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentListEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDocuments(loadDocumentRegistry());
  }, []);

  async function handleUpload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocument(file);
      upsertDocumentEntry({
        documentId: result.document_id,
        filename: result.metadata.filename,
        uploadedAt: new Date().toISOString(),
        pageCount: result.page_count,
        detectionCount: 0,
        reviewPercentage: 0,
        overallRisk: 0,
        exportReady: false,
      });
      setDocuments(loadDocumentRegistry());
      router.push(`/document/${result.document_id}`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <AppLayout>
      <div className="flex min-h-0 flex-1 flex-col gap-4 p-6">
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              Dashboard
            </p>
            <h1 className="mt-1 text-2xl font-medium text-slate-50">Human review workbench</h1>
            <p className="mt-1 max-w-2xl text-sm text-[var(--muted-foreground)]">
              Upload a document, review AI detections in risk-priority order, and export only after
              backend validation passes.
            </p>
          </div>
        </header>

        <UploadZone uploading={uploading} onUpload={handleUpload} error={error} />

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-100">Documents</h2>
            <span className="text-[11px] text-[var(--muted-foreground)]">{documents.length} total</span>
          </div>

          {documents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border-subtle)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">
              No documents yet. Upload a TXT, PDF, or DOCX file to begin review.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {documents.map((doc) => (
                <DocumentCard key={doc.documentId} document={doc} />
              ))}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}

function UploadZone({
  uploading,
  onUpload,
  error,
}: {
  uploading: boolean;
  onUpload: (file: File) => void;
  error: string | null;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border-subtle)] bg-[rgba(9,11,20,0.6)] px-6 py-10 transition",
        "hover:border-sky-500/40 hover:bg-sky-500/5",
      )}
    >
      <input
        type="file"
        accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        disabled={uploading}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(file);
        }}
      />
      {uploading ? (
        <Loader2 className="h-6 w-6 animate-spin text-sky-300" />
      ) : (
        <FileUp className="h-6 w-6 text-sky-300" />
      )}
      <p className="mt-3 text-sm text-slate-100">
        {uploading ? "Uploading and extracting text…" : "Drop a document or click to upload"}
      </p>
      <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">TXT · PDF · DOCX</p>
      {error && <p className="mt-3 text-[11px] text-rose-300">{error}</p>}
    </label>
  );
}

function DocumentCard({ document }: { document: DocumentListEntry }) {
  return (
    <Link
      href={`/document/${document.documentId}`}
      className="rounded-xl border border-[var(--border-subtle)] bg-[rgba(9,11,20,0.96)] p-4 transition hover:border-sky-500/40 hover:bg-sky-500/5"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="line-clamp-2 text-sm font-medium text-slate-100">{document.filename}</p>
          <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
            {new Date(document.uploadedAt).toLocaleString()}
          </p>
        </div>
        <div
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-mono",
            document.exportReady
              ? "bg-emerald-500/10 text-emerald-100"
              : "bg-amber-500/10 text-amber-100",
          )}
        >
          {document.exportReady ? "Ready" : "Review"}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-[10px] text-[var(--muted-foreground)]">
        <Metric label="Pages" value={String(document.pageCount)} />
        <Metric label="Detections" value={String(document.detectionCount)} />
        <Metric label="Reviewed" value={`${document.reviewPercentage}%`} />
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-amber-100/90">
        <ShieldAlert className="h-3.5 w-3.5" />
        <span>Risk score {document.overallRisk}</span>
      </div>
    </Link>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-black/20 px-2 py-1.5">
      <div className="uppercase tracking-[0.14em]">{label}</div>
      <div className="mt-0.5 font-mono text-slate-100">{value}</div>
    </div>
  );
}
