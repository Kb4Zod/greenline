import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api";
import type { ImportBatch, ImportReceipt } from "../types";
import { fmtDate } from "../format";

export default function ImportView() {
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [receipt, setReceipt] = useState<ImportReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => api.imports().then(setBatches);
  useEffect(() => {
    refresh();
  }, []);

  const handleFile = async (file: File) => {
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      setReceipt(await api.upload(file));
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.detail && typeof e.detail === "object") {
        const detail = e.detail as { message?: string; rows?: { row: number; reason: string }[] };
        const rows = detail.rows
          ?.slice(0, 5)
          .map((r) => `row ${r.row}: ${r.reason}`)
          .join("; ");
        setError([detail.message, rows].filter(Boolean).join(" "));
      } else {
        setError("Import failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="rise">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        onClick={() => fileInput.current?.click()}
        className={
          "cursor-pointer rounded-2xl border border-dashed px-8 py-14 text-center transition-colors " +
          (dragging
            ? "border-go bg-go/5 text-go"
            : "border-ink-line text-paper-dim hover:border-paper-faint")
        }
      >
        <p className="text-lg">
          {busy ? "Importing…" : "Drop a bank CSV here, or click to choose"}
        </p>
        <p className="mt-2 text-sm text-paper-faint">
          Files are read locally and never leave this machine.
        </p>
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {receipt && (
        <div className="mt-4 rounded-xl bg-ink-raised px-4 py-3 text-sm">
          <span className="text-go">✓ {receipt.filename}</span>
          <span className="text-paper-dim">
            {" "}— {receipt.rows_total} rows · {receipt.rows_added} added ·{" "}
            {receipt.rows_duplicate} duplicates
            {receipt.rows_added === 0 && " (already imported)"}
          </span>
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-xl border border-stop/40 bg-stop/10 px-4 py-3 text-sm text-stop">
          {error}
        </div>
      )}

      {batches.length > 0 && (
        <section className="mt-10">
          <h2 className="text-paper-dim text-sm tracking-widest uppercase mb-3">History</h2>
          <ul className="divide-y divide-ink-line rounded-xl bg-ink-raised px-4 text-sm">
            {batches.map((batch) => (
              <li key={batch.id} className="flex justify-between gap-4 py-2.5">
                <span className="text-paper truncate">{batch.filename}</span>
                <span className="text-paper-dim shrink-0">
                  {batch.date_min && batch.date_max && (
                    <>
                      {fmtDate(batch.date_min)} – {fmtDate(batch.date_max)} ·{" "}
                    </>
                  )}
                  <span className="text-paper">{batch.rows_added}</span> added ·{" "}
                  {batch.rows_duplicate} dup
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
