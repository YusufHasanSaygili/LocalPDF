"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { StatusCard } from "@/components/StatusCard";
import { api, ApiError, apiUrl, idempotencyKey } from "@/lib/api";
import type { AuditEvent, Document, Job, Preview } from "@/lib/types";

const CATEGORIES = [
  {
    label: "Organize PDF",
    tools: [
      ["merge", "Merge PDF", "⇉"], ["split", "Split PDF", "➂"],
      ["remove_pages", "Remove pages", "✕"], ["extract_pages", "Extract pages", "↥"],
      ["reorder", "Organize PDF", "↕"], ["scan_to_pdf", "Scan to PDF", "▣"],
    ],
  },
  {
    label: "Optimize PDF",
    tools: [["compress", "Compress PDF", "⇲"], ["repair", "Repair PDF", "⚒"], ["ocr", "OCR PDF", "Aa"]],
  },
  {
    label: "Convert to PDF",
    tools: [
      ["jpg_to_pdf", "JPG to PDF", "IMG"], ["word_to_pdf", "WORD to PDF", "W"],
      ["powerpoint_to_pdf", "POWERPOINT to PDF", "P"], ["excel_to_pdf", "EXCEL to PDF", "X"],
      ["html_to_pdf", "HTML to PDF", "<>"],
    ],
  },
  {
    label: "Convert from PDF",
    tools: [
      ["pdf_to_jpg", "PDF to JPG", "IMG"], ["pdf_to_word", "PDF to WORD", "W"],
      ["pdf_to_powerpoint", "PDF to POWERPOINT", "P"], ["pdf_to_excel", "PDF to EXCEL", "X"],
      ["pdf_to_pdfa", "PDF to PDF/A", "A"],
    ],
  },
  {
    label: "Edit PDF",
    tools: [
      ["rotate", "Rotate PDF", "↻"], ["page_numbers", "Add page numbers", "#"],
      ["watermark", "Add watermark", "W"], ["crop", "Crop PDF", "⌗"],
      ["edit_pdf", "Edit PDF", "✎"], ["pdf_forms", "PDF Forms", "▤"],
    ],
  },
  {
    label: "PDF Security",
    tools: [
      ["unlock", "Unlock PDF", "🔓"], ["protect", "Protect PDF", "🔒"],
      ["signature", "Sign PDF", "✒"], ["redact", "Redact PDF", "■"],
      ["compare", "Compare PDF", "≠"],
    ],
  },
  {
    label: "PDF Intelligence",
    tools: [["summarize", "AI Summarizer", "✦"], ["translate", "Translate PDF", "A文"], ["pdf_to_markdown", "PDF to Markdown", "MD"]],
  },
] as const;

const TOOLS = CATEGORIES.flatMap((category) => category.tools.map(([id, label, glyph]) => ({ id, label, glyph, category: category.label })));
type ToolId = (typeof TOOLS)[number]["id"];
const MULTI_TOOLS = new Set<ToolId>(["merge", "compare", "scan_to_pdf", "jpg_to_pdf"]);
const ORIGINAL_TOOLS = new Set<ToolId>(["scan_to_pdf", "jpg_to_pdf", "word_to_pdf", "powerpoint_to_pdf", "excel_to_pdf", "html_to_pdf", "unlock"]);

function humanBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; value >= 1024 && index < units.length; index += 1) { value /= 1024; unit = units[index]; }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${unit}`;
}

function shortHash(hash: string) { return `${hash.slice(0, 8)}…${hash.slice(-6)}`; }

export function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pickedIds, setPickedIds] = useState<string[]>([]);
  const [tool, setTool] = useState<ToolId>("merge");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [previews, setPreviews] = useState<Preview[]>([]);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [search, setSearch] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const selected = documents.find((document) => document.id === selectedId) ?? documents[0] ?? null;
  const filtered = useMemo(() => documents.filter((document) => document.display_name.toLowerCase().includes(search.toLowerCase())), [documents, search]);

  const loadDocuments = useCallback(async () => {
    try {
      const payload = await api<{ items: Document[] }>("/documents");
      setDocuments(payload.items);
      setSelectedId((current) => current ?? payload.items[0]?.id ?? null);
      setError(null);
    } catch (caught) { setError(asApiError(caught)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => void loadDocuments(), [loadDocuments]);
  useEffect(() => {
    setAudit(null);
    if (!selected || selected.media_type !== "application/pdf" && !selected.latest_version) { setPreviews([]); return; }
    const source = selected.latest_version ? { kind: "version", id: selected.latest_version.id } : { kind: "original", id: selected.original.id };
    let cancelled = false;
    let attempts = 0;
    const refresh = async () => {
      try {
        const payload = await api<{ items: Preview[] }>(`/sources/${source.kind}/${source.id}/previews`);
        if (cancelled) return;
        setPreviews(payload.items);
        const expected = selected.latest_version?.page_count ?? selected.original.page_count ?? 1;
        if (payload.items.length >= expected || attempts++ > 30) return;
        window.setTimeout(refresh, 1000);
      } catch { if (!cancelled && attempts++ < 15) window.setTimeout(refresh, 1000); }
    };
    void refresh();
    return () => { cancelled = true; };
  }, [selected]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true); setError(null);
    try {
      for (const file of Array.from(files)) {
        const body = new FormData(); body.append("file", file);
        await api("/documents", { method: "POST", headers: { "Idempotency-Key": idempotencyKey() }, body });
      }
      await loadDocuments();
    } catch (caught) { setError(asApiError(caught)); }
    finally { setBusy(false); if (fileInput.current) fileInput.current.value = ""; }
  }

  async function pollJob(jobId: string): Promise<Job> {
    for (;;) {
      const latest = await api<Job>(`/jobs/${jobId}`); setJob(latest);
      if (["succeeded", "failed", "cancelled"].includes(latest.state)) return latest;
      await new Promise((resolve) => window.setTimeout(resolve, latest.state === "queued" ? 500 : 900));
    }
  }

  async function runOperation(parameters: Record<string, unknown>) {
    if (!selected) return;
    setBusy(true); setError(null); setJob(null);
    try {
      const sourceDocuments = MULTI_TOOLS.has(tool) ? documents.filter((document) => pickedIds.includes(document.id)) : [selected];
      const inputs = sourceDocuments.map((document) => {
        if (!ORIGINAL_TOOLS.has(tool) && document.latest_version) return { kind: "version", id: document.latest_version.id };
        return { kind: "original", id: document.original.id };
      });
      const queued = await api<{ job: Job }>("/operations", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey() },
        body: JSON.stringify({ type: tool, inputs, parameters }),
      });
      const result = await pollJob(queued.job.id);
      if (result.state !== "succeeded") throw new ApiError(result.error?.code ?? "JOB_FAILED", result.error?.message ?? "The operation failed.");
      const downloadUrl = result.result?.download_url;
      if (typeof downloadUrl === "string") window.location.href = apiUrl(downloadUrl);
      await loadDocuments();
    } catch (caught) { setError(asApiError(caught)); }
    finally { setBusy(false); }
  }

  async function loadAudit() {
    if (!selected) return;
    try { setAudit((await api<{ items: AuditEvent[] }>(`/documents/${selected.id}/events`)).items); }
    catch (caught) { setError(asApiError(caught)); }
  }

  async function exportDocument() {
    if (!selected) return;
    setBusy(true);
    try {
      const response = await api<{ job_id: string }>(`/documents/${selected.id}/export`);
      const result = await pollJob(response.job_id);
      if (result.state !== "succeeded") throw new ApiError("EXPORT_FAILED", "Export failed.");
      window.location.href = apiUrl(`/api/v1/exports/${result.id}/download`);
    } catch (caught) { setError(asApiError(caught)); }
    finally { setBusy(false); }
  }

  async function deleteDocument() {
    if (!selected || !window.confirm(`Delete "${selected.display_name}" from LocalPDF?`)) return;
    setBusy(true);
    try {
      const response = await api<{ job_id: string | null }>(`/documents/${selected.id}`, { method: "DELETE", headers: { "Idempotency-Key": idempotencyKey(), "X-Confirm-Delete": "delete" } });
      if (response.job_id) await pollJob(response.job_id);
      setSelectedId(null); await loadDocuments();
    } catch (caught) { setError(asApiError(caught)); }
    finally { setBusy(false); }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">L</span><span>LocalPDF <small>2.0</small></span></div>
        <nav aria-label="Main menu">
          <button className="nav-item active"><span>◱</span> Documents</button>
          <button className="nav-item" onClick={() => fileInput.current?.click()}><span>+</span> Add files</button>
        </nav>
        <div className="sidebar-section tool-catalog">
          {CATEGORIES.map((category) => <div className="tool-category" key={category.label}>
            <span className="eyebrow">{category.label}</span>
            {category.tools.map(([id, label, glyph]) => <button className={`nav-item ${tool === id ? "tool-active" : ""}`} key={id} onClick={() => setTool(id)}><span>{glyph}</span>{label}</button>)}
          </div>)}
        </div>
        <div className="privacy-badge"><span>●</span><div><strong>100% local</strong><small>Your files never leave this PC</small></div></div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">Private desktop workspace</span><h1>PDF Toolbox</h1></div>
          <div className="header-actions">
            <label className="search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search files" /></label>
            <button className="button primary" onClick={() => fileInput.current?.click()} disabled={busy}>+ Add files</button>
            <input ref={fileInput} className="visually-hidden" type="file" multiple accept=".pdf,.docx,.xlsx,.pptx,.jpg,.jpeg,.png,.tif,.tiff,.bmp,.webp,.html,.htm" onChange={(event) => void upload(event.target.files)} />
          </div>
        </header>
        <div className="scope-banner"><span>ⓘ</span><span>Docker-free desktop app. All processing runs locally on this computer.</span></div>
        {error && <StatusCard tone="error" title={error.code}>{error.message}</StatusCard>}
        {job && !["succeeded", "failed", "cancelled"].includes(job.state) && <StatusCard tone="info" title="Processing locally"><div className="progress"><span style={{ width: `${Math.max(4, job.progress_percent)}%` }} /></div><small>{job.progress_percent}% complete</small></StatusCard>}
        {job?.state === "succeeded" && <StatusCard tone="success" title="Done">The result is ready. The original file was kept unchanged.</StatusCard>}

        <div className="content-grid">
          <section className="library-panel">
            <div className="panel-heading"><div><h2>Files</h2><span>{documents.length} items</span></div></div>
            {loading ? <div className="skeleton-list"><i /><i /><i /></div> : filtered.length === 0 ?
              <div className="empty-state"><span className="empty-icon">+</span><h3>Add your first file</h3><p>PDF, Office, image and HTML files are supported.</p><button className="button primary" onClick={() => fileInput.current?.click()}>Choose files</button></div> :
              <div className="document-list">{filtered.map((document) => <article className={`document-row ${selected?.id === document.id ? "selected" : ""}`} key={document.id} onClick={() => setSelectedId(document.id)}>
                <label className="merge-check" title="Add to multi-file selection" onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={pickedIds.includes(document.id)} onChange={(event) => setPickedIds((current) => event.target.checked ? [...current, document.id] : current.filter((id) => id !== document.id))} /></label>
                <span className={`file-icon ${document.media_type === "application/pdf" ? "pdf" : "office"}`}>{document.display_name.split(".").pop()?.slice(0, 4).toUpperCase()}</span>
                <div className="document-main"><strong>{document.display_name}</strong><span>{document.original.page_count ? `${document.original.page_count} pages · ` : ""}{humanBytes(document.original.byte_size)}</span></div>
                <div className="document-meta"><code>{shortHash(document.latest_version?.sha256 ?? document.original.sha256)}</code>{document.latest_version && <span className="version-pill">v{document.latest_version.version_number}</span>}</div>
              </article>)}</div>}
          </section>

          <aside className="detail-panel">{selected ? <>
            <div className="detail-title"><div><span className="eyebrow">Selected file</span><h2>{selected.display_name}</h2></div><span className="state-pill">● {selected.state}</span></div>
            <div className="hash-card"><span>SHA-256</span><code>{selected.latest_version?.sha256 ?? selected.original.sha256}</code><button onClick={() => void navigator.clipboard.writeText(selected.latest_version?.sha256 ?? selected.original.sha256)}>Copy</button></div>
            <div className="preview-strip">{previews.slice(0, 4).map((preview) => <figure key={preview.id}><img src={apiUrl(preview.content_url)} alt={`Page ${preview.page_number}`} /><figcaption>{preview.page_number}</figcaption></figure>)}</div>
            <ToolPanel tool={tool} document={selected} pickedCount={pickedIds.length} busy={busy} onRun={runOperation} />
            <div className="detail-actions">
              <a className="button secondary" href={apiUrl(selected.latest_version?.download_url ?? selected.original.download_url)}>↓ Download</a>
              <button className="button ghost" onClick={() => void loadAudit()}>Audit</button>
              <button className="button ghost" onClick={() => void exportDocument()}>Export ZIP</button>
              <button className="button danger" onClick={() => void deleteDocument()}>Delete</button>
            </div>
            {audit && <AuditTimeline events={audit} />}
          </> : <div className="empty-state compact"><h3>Select a file</h3></div>}</aside>
        </div>
      </section>
    </main>
  );
}

function ToolPanel({ tool, document, pickedCount, busy, onRun }: { tool: ToolId; document: Document; pickedCount: number; busy: boolean; onRun: (parameters: Record<string, unknown>) => Promise<void> }) {
  const [pages, setPages] = useState("1");
  const [ranges, setRanges] = useState("1");
  const [profile, setProfile] = useState("balanced");
  const [text, setText] = useState("CONFIDENTIAL");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("field_1");
  const [sourceLanguage, setSourceLanguage] = useState("en");
  const [targetLanguage, setTargetLanguage] = useState("tr");
  const [signer, setSigner] = useState("");
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const selectedTool = TOOLS.find((item) => item.id === tool)!;
  const pageValues = () => pages.split(",").map((value) => Number(value.trim())).filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (tool === "signature") {
      let versionId = document.latest_version?.id;
      if (!versionId) {
        const prepared = await api<{ job: Job }>("/operations", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey() },
          body: JSON.stringify({ type: "repair", inputs: [{ kind: "original", id: document.original.id }], parameters: {} }),
        });
        for (;;) {
          const latest = await api<Job>(`/jobs/${prepared.job.id}`);
          if (latest.state === "failed") throw new ApiError(latest.error?.code ?? "SIGN_PREPARE_FAILED", latest.error?.message ?? "The PDF could not be prepared for signing.");
          if (latest.state === "succeeded") { versionId = latest.result_ids[0]; break; }
          await new Promise((resolve) => window.setTimeout(resolve, 700));
        }
      }
      if (!versionId) throw new ApiError("SIGN_PREPARE_FAILED", "The PDF could not be prepared for signing.");
      const created = await api<{ id: string }>("/signature-requests", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey() }, body: JSON.stringify({ version_id: versionId, signer: { display_name: signer }, fields: [{ type: "signature", page_number: 1, x_pt: 72, y_pt: 72, width_pt: 180, height_pt: 48, required: true }] }) });
      const invited = await api<{ manual_url: string }>(`/signature-requests/${created.id}/invite`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey() } });
      setManualUrl(invited.manual_url); return;
    }
    const parameters: Record<string, unknown> = {};
    if (tool === "split") Object.assign(parameters, { mode: "range", ranges });
    if (["remove_pages", "extract_pages"].includes(tool)) parameters.pages = ranges;
    if (tool === "reorder") parameters.pages = pageValues();
    if (tool === "rotate") Object.assign(parameters, { pages: pageValues(), degrees: 90 });
    if (tool === "compress") parameters.profile = profile;
    if (tool === "watermark") Object.assign(parameters, { text, opacity: 0.2, rotation: -35, font_size: 38, pages: [] });
    if (tool === "redact") Object.assign(parameters, { rectangles: [{ page_number: 1, x_pt: 72, y_pt: 72, width_pt: 180, height_pt: 48 }], remove_metadata: true });
    if (tool === "page_numbers") Object.assign(parameters, { prefix: text === "CONFIDENTIAL" ? "" : text, font_size: 10 });
    if (tool === "crop") Object.assign(parameters, { left: 20, top: 20, right: 20, bottom: 20 });
    if (tool === "edit_pdf") Object.assign(parameters, { text, page_number: 1, x: 72, y: 72, font_size: 14 });
    if (tool === "pdf_forms") Object.assign(parameters, { name, value: text === "CONFIDENTIAL" ? "" : text, page_number: 1, x: 72, y: 72, width: 240, height: 34 });
    if (["unlock", "protect"].includes(tool)) parameters.password = password;
    if (tool === "summarize") parameters.max_sentences = 8;
    if (tool === "translate") Object.assign(parameters, { source_language: sourceLanguage, target_language: targetLanguage });
    await onRun(parameters);
  }

  const needsTwo = tool === "merge" || tool === "compare";
  const blocked = needsTwo && pickedCount < 2 || ["scan_to_pdf", "jpg_to_pdf"].includes(tool) && pickedCount < 1;
  return <form className="tool-panel" onSubmit={(event) => void submit(event)}>
    <div className="tool-heading"><span className="tool-glyph">{selectedTool.glyph}</span><div><span className="eyebrow">{selectedTool.category}</span><h3>{selectedTool.label}</h3></div></div>
    {MULTI_TOOLS.has(tool) && <p>Use the checkboxes in the file list. <strong>{pickedCount} selected</strong></p>}
    {tool === "split" && <label>Page ranges<input value={ranges} onChange={(event) => setRanges(event.target.value)} placeholder="1-3,5,8-10" /></label>}
    {["remove_pages", "extract_pages"].includes(tool) && <label>Pages<input value={ranges} onChange={(event) => setRanges(event.target.value)} placeholder="1-3,5" /></label>}
    {tool === "reorder" && <label>New page order<input value={pages} onChange={(event) => setPages(event.target.value)} placeholder="3,1,2" /></label>}
    {tool === "rotate" && <label>Pages to rotate<input value={pages} onChange={(event) => setPages(event.target.value)} placeholder="1,3" /></label>}
    {tool === "compress" && <label>Compression profile<select value={profile} onChange={(event) => setProfile(event.target.value)}><option value="lossless">Lossless</option><option value="balanced">Balanced</option><option value="smallest">Smallest</option></select></label>}
    {["watermark", "edit_pdf", "page_numbers"].includes(tool) && <label>{tool === "page_numbers" ? "Optional prefix" : "Text"}<input value={text} onChange={(event) => setText(event.target.value)} /></label>}
    {tool === "pdf_forms" && <><label>Field name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Default value<input value={text} onChange={(event) => setText(event.target.value)} /></label></>}
    {["unlock", "protect"].includes(tool) && <label>PDF password<input type="password" value={password} minLength={tool === "protect" ? 4 : 1} onChange={(event) => setPassword(event.target.value)} required /></label>}
    {tool === "translate" && <div className="field-row"><label>From<select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value)}><option value="en">English</option><option value="tr">Turkish</option></select></label><label>To<select value={targetLanguage} onChange={(event) => setTargetLanguage(event.target.value)}><option value="tr">Turkish</option><option value="en">English</option></select></label></div>}
    {tool === "redact" && <p>Applies a permanent redaction box to page 1. The original remains unchanged.</p>}
    {tool === "crop" && <p>Crops 20 points from every edge. The output is saved as a new version.</p>}
    {tool === "ocr" && <p>Offline OCR adds an invisible searchable text layer. No Tesseract or Docker install is required.</p>}
    {tool === "signature" && <><label>Signer label<input value={signer} onChange={(event) => setSigner(event.target.value)} placeholder="Full name" required /></label><p className="scope-inline">Signature-lite records consent and seals the document hash; it is not a qualified electronic signature.</p>{manualUrl && <div className="manual-link"><code>{`${window.location.origin}${manualUrl}`}</code><button type="button" onClick={() => void navigator.clipboard.writeText(`${window.location.origin}${manualUrl}`)}>Copy</button></div>}</>}
    <button className="button primary wide" disabled={busy || blocked} type="submit">{busy ? "Processing…" : blocked ? "Select the required files" : `Run ${selectedTool.label}`}</button>
  </form>;
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  return <section className="audit"><div className="panel-heading"><h3>Append-only audit</h3><span>{events.length} events</span></div>{events.map((event) => <div className="audit-row" key={event.id}><span className="audit-dot" /><div><strong>{event.event_type}</strong><small>{new Date(event.occurred_at).toLocaleString()}</small>{event.output_sha256 && <code>{shortHash(event.output_sha256)}</code>}</div></div>)}</section>;
}

function asApiError(error: unknown) { return error instanceof ApiError ? error : new ApiError("UNEXPECTED_ERROR", error instanceof Error ? error.message : "Unexpected error."); }
