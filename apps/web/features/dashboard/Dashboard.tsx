"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { StatusCard } from "@/components/StatusCard";
import { api, ApiError, apiUrl, idempotencyKey } from "@/lib/api";
import type { AuditEvent, Document, Job, Preview } from "@/lib/types";

const TOOLS = [
  { id: "merge", label: "Birleştir", glyph: "⇉" },
  { id: "split", label: "Böl", glyph: "⑂" },
  { id: "reorder", label: "Sırala", glyph: "↕" },
  { id: "rotate", label: "Döndür", glyph: "↻" },
  { id: "compress", label: "Sıkıştır", glyph: "⇲" },
  { id: "watermark", label: "Filigran", glyph: "W" },
  { id: "redact", label: "Redaksiyon", glyph: "■" },
  { id: "ocr", label: "OCR", glyph: "Aa" },
  { id: "office_to_pdf", label: "Office → PDF", glyph: "▣" },
  { id: "signature", label: "Signature-lite", glyph: "✦" },
] as const;

type ToolId = (typeof TOOLS)[number]["id"];

function humanBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; value >= 1024 && index < units.length; index += 1) {
    value /= 1024;
    unit = units[index];
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${unit}`;
}

function shortHash(hash: string) {
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`;
}

export function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mergeIds, setMergeIds] = useState<string[]>([]);
  const [tool, setTool] = useState<ToolId>("merge");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [previews, setPreviews] = useState<Preview[]>([]);
  const [previewState, setPreviewState] = useState<"idle" | "loading" | "partial" | "ready" | "error">("idle");
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [search, setSearch] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const selected = documents.find((document) => document.id === selectedId) ?? documents[0] ?? null;
  const filtered = useMemo(
    () => documents.filter((document) => document.display_name.toLocaleLowerCase("tr").includes(search.toLocaleLowerCase("tr"))),
    [documents, search],
  );

  const loadDocuments = useCallback(async () => {
    try {
      const payload = await api<{ items: Document[] }>("/documents");
      setDocuments(payload.items);
      setSelectedId((current) => current ?? payload.items[0]?.id ?? null);
      setError(null);
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void loadDocuments(), [loadDocuments]);

  useEffect(() => {
    setAudit(null);
    if (!selected) {
      setPreviews([]);
      setPreviewState("idle");
      return;
    }
    const source = selected.latest_version
      ? { kind: "version", id: selected.latest_version.id }
      : { kind: "original", id: selected.original.id };
    let cancelled = false;
    let attempts = 0;
    const expected = selected.latest_version?.page_count ?? selected.original.page_count ?? 1;
    const refresh = async () => {
      setPreviewState((current) => current === "idle" ? "loading" : current);
      try {
        const payload = await api<{ items: Preview[] }>(`/sources/${source.kind}/${source.id}/previews`);
        if (cancelled) return;
        setPreviews(payload.items);
        if (payload.items.length >= expected) {
          setPreviewState("ready");
          return;
        }
        setPreviewState(payload.items.length ? "partial" : "loading");
      } catch {
        if (!cancelled) setPreviewState("error");
        return;
      }
      attempts += 1;
      if (attempts < 40) window.setTimeout(refresh, 1500);
      else if (!cancelled) setPreviewState("error");
    };
    void refresh();
    return () => { cancelled = true; };
  }, [selected]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const body = new FormData();
        body.append("file", file);
        await api("/documents", {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey() },
          body,
        });
      }
      await loadDocuments();
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function pollJob(jobId: string): Promise<Job> {
    for (;;) {
      const latest = await api<Job>(`/jobs/${jobId}`);
      setJob(latest);
      if (["succeeded", "failed", "cancelled"].includes(latest.state)) return latest;
      await new Promise((resolve) => window.setTimeout(resolve, latest.state === "queued" ? 700 : 1200));
    }
  }

  async function runOperation(parameters: Record<string, unknown>) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const inputDocuments = tool === "merge"
        ? documents.filter((document) => mergeIds.includes(document.id))
        : [selected];
      const inputs = inputDocuments.map((document) => {
        if (tool !== "office_to_pdf" && document.latest_version) {
          return { kind: "version", id: document.latest_version.id };
        }
        return { kind: "original", id: document.original.id };
      });
      const response = await api<{ job: Job }>("/operations", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey() },
        body: JSON.stringify({ type: tool, inputs, parameters }),
      });
      setJob(response.job);
      const result = await pollJob(response.job.id);
      if (result.state === "failed") {
        throw new ApiError(result.error?.code ?? "JOB_FAILED", result.error?.message ?? "İşlem tamamlanamadı.");
      }
      await loadDocuments();
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function loadAudit() {
    if (!selected) return;
    try {
      const payload = await api<{ items: AuditEvent[] }>(`/documents/${selected.id}/events`);
      setAudit(payload.items);
    } catch (caught) {
      setError(asApiError(caught));
    }
  }

  async function exportDocument() {
    if (!selected) return;
    setBusy(true);
    try {
      const response = await api<{ job_id: string }>(`/documents/${selected.id}/export`);
      const result = await pollJob(response.job_id);
      if (result.state !== "succeeded") throw new ApiError("EXPORT_FAILED", "Dışa aktarma tamamlanamadı.");
      window.location.href = apiUrl(`/api/v1/exports/${result.id}/download`);
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function deleteDocument() {
    if (!selected || !window.confirm(`“${selected.display_name}” uygulama deposundan silinsin mi? Backup kopyaları etkilenmez.`)) return;
    setBusy(true);
    try {
      const response = await api<{ job_id: string | null }>(`/documents/${selected.id}`, {
        method: "DELETE",
        headers: { "Idempotency-Key": idempotencyKey(), "X-Confirm-Delete": "delete" },
      });
      if (response.job_id) await pollJob(response.job_id);
      setSelectedId(null);
      await loadDocuments();
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function createBackup() {
    setBusy(true);
    setError(null);
    try {
      const queued = await api<Job>("/maintenance/backups", {
        method: "POST",
        headers: { "X-Confirm-Backup": "backup-local-data" },
      });
      setJob(queued);
      const result = await pollJob(queued.id);
      if (result.state !== "succeeded") {
        throw new ApiError(result.error?.code ?? "BACKUP_FAILED", result.error?.message ?? "Backup tamamlanamadı.");
      }
      window.location.href = apiUrl(`/api/v1/exports/${result.id}/download`);
    } catch (caught) {
      setError(asApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">L</span><span>LocalPDF</span></div>
        <nav aria-label="Ana menü">
          <button className="nav-item active"><span>▱</span> Belgeler</button>
          <button className="nav-item" onClick={() => fileInput.current?.click()}><span>＋</span> Yeni yükleme</button>
        </nav>
        <div className="sidebar-section">
          <span className="eyebrow">Araçlar</span>
          {TOOLS.map((item) => (
            <button
              className={`nav-item ${tool === item.id ? "tool-active" : ""}`}
              key={item.id}
              onClick={() => setTool(item.id)}
            >
              <span>{item.glyph}</span>{item.label}
            </button>
          ))}
        </div>
        <div className="privacy-badge"><span>●</span><div><strong>Tamamen yerel</strong><small>Dosyalar cihazından çıkmaz</small></div></div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">Kişisel belge çalışma alanı</span><h1>Belgelerim</h1></div>
          <div className="header-actions">
            <label className="search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Belgelerde ara" /></label>
            <button className="button ghost" onClick={() => void createBackup()} disabled={busy}>◇ Backup</button>
            <button className="button primary" onClick={() => fileInput.current?.click()} disabled={busy}>＋ Dosya yükle</button>
            <input ref={fileInput} className="visually-hidden" type="file" multiple accept=".pdf,.docx,.xlsx,.pptx" onChange={(event) => void upload(event.target.files)} />
          </div>
        </header>

        <div className="scope-banner"><span>ⓘ</span><span>Düşük riskli kişisel kullanım içindir. Nitelikli elektronik imza veya kimlik doğrulama sağlamaz.</span></div>

        {error && <StatusCard tone="error" title={error.code}>{error.message}{error.correlationId && <small>İzleme kodu: {error.correlationId}</small>}</StatusCard>}

        {job && !["succeeded", "failed", "cancelled"].includes(job.state) && (
          <StatusCard tone="info" title={job.state === "queued" ? "İşlem kuyrukta" : "Belge işleniyor"}>
            <div className="progress"><span style={{ width: `${Math.max(4, job.progress_percent)}%` }} /></div>
            <small aria-live="polite">%{job.progress_percent} · Sayfayı kapatsan da işlem worker üzerinde sürer.</small>
          </StatusCard>
        )}
        {job?.state === "succeeded" && <StatusCard tone="success" title="Yeni sürüm hazır">Orijinal korunarak hash’lenmiş bir çıktı oluşturuldu.</StatusCard>}

        <div className="content-grid">
          <section className="library-panel">
            <div className="panel-heading"><div><h2>Kütüphane</h2><span>{documents.length} belge</span></div></div>
            {loading ? (
              <div className="skeleton-list" aria-label="Belgeler yükleniyor"><i /><i /><i /></div>
            ) : filtered.length === 0 ? (
              <div className="empty-state"><span className="empty-icon">＋</span><h3>Henüz belge yok</h3><p>PDF veya Office dosyalarını buraya ekle. Orijinaller değişmeden saklanır.</p><button className="button primary" onClick={() => fileInput.current?.click()}>İlk dosyanı seç</button></div>
            ) : (
              <div className="document-list">
                {filtered.map((document) => (
                  <article className={`document-row ${selected?.id === document.id ? "selected" : ""}`} key={document.id} onClick={() => setSelectedId(document.id)}>
                    <label className="merge-check" title="Birleştirme listesine ekle" onClick={(event) => event.stopPropagation()}>
                      <input type="checkbox" checked={mergeIds.includes(document.id)} onChange={(event) => setMergeIds((current) => event.target.checked ? [...current, document.id] : current.filter((id) => id !== document.id))} />
                    </label>
                    <span className={`file-icon ${document.media_type === "application/pdf" ? "pdf" : "office"}`}>{document.media_type === "application/pdf" ? "PDF" : "DOC"}</span>
                    <div className="document-main"><strong>{document.display_name}</strong><span>{document.original.page_count ? `${document.original.page_count} sayfa · ` : ""}{humanBytes(document.original.byte_size)} · {new Date(document.created_at).toLocaleDateString("tr-TR")}</span></div>
                    <div className="document-meta"><code>{shortHash(document.latest_version?.sha256 ?? document.original.sha256)}</code>{document.latest_version && <span className="version-pill">v{document.latest_version.version_number}</span>}</div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <aside className="detail-panel">
            {selected ? (
              <>
                <div className="detail-title"><div><span className="eyebrow">Seçili belge</span><h2>{selected.display_name}</h2></div><span className="state-pill">● {selected.state}</span></div>
                <div className="hash-card"><span>SHA-256</span><code title={selected.latest_version?.sha256 ?? selected.original.sha256}>{selected.latest_version?.sha256 ?? selected.original.sha256}</code><button onClick={() => void navigator.clipboard.writeText(selected.latest_version?.sha256 ?? selected.original.sha256)}>Kopyala</button></div>
                {selected.original.detected_features.warnings?.length ? <Warnings warnings={selected.original.detected_features.warnings} /> : null}
                <div className="preview-strip">
                  {previews.slice(0, 4).map((preview) => <figure key={preview.id}><img src={apiUrl(preview.content_url)} alt={`Sayfa ${preview.page_number} önizlemesi`} /><figcaption>{preview.page_number}</figcaption></figure>)}
                  {!previews.length && selected.media_type === "application/pdf" && <p>{previewState === "error" ? "Önizleme üretilemedi; belgeyi yine de işleyebilirsin." : "Önizleme hazırlanıyor…"}</p>}
                </div>
                <ToolPanel tool={tool} document={selected} mergeCount={mergeIds.length} busy={busy} onRun={runOperation} onSignatureResult={(message) => setJob(message)} />
                <div className="detail-actions">
                  <a className="button secondary" href={apiUrl(selected.latest_version?.download_url ?? selected.original.download_url)}>↓ İndir</a>
                  <button className="button ghost" onClick={() => void loadAudit()}>Audit</button>
                  <button className="button ghost" onClick={() => void exportDocument()}>ZIP dışa aktar</button>
                  <button className="button danger" onClick={() => void deleteDocument()}>Sil</button>
                </div>
                {audit && <AuditTimeline events={audit} />}
              </>
            ) : <div className="empty-state compact"><h3>Bir belge seç</h3><p>Önizleme, hash ve araçlar burada görünecek.</p></div>}
          </aside>
        </div>
      </section>
    </main>
  );
}

function Warnings({ warnings }: { warnings: string[] }) {
  const copy: Record<string, string> = {
    may_change_fonts: "Font görünümü işlem sırasında değişebilir.",
    may_flatten_forms: "Form alanları düzleşebilir veya değişebilir.",
    invalidates_signature: "Mevcut dijital imza, yeni sürümde geçersiz olabilir.",
    office_layout_may_change: "Office düzeni ve sayfa kırımları dönüşümde değişebilir.",
  };
  return <div className="warning-list">{warnings.map((warning) => <span key={warning}>△ {copy[warning] ?? warning}</span>)}</div>;
}

function ToolPanel({ tool, document, mergeCount, busy, onRun, onSignatureResult }: {
  tool: ToolId;
  document: Document;
  mergeCount: number;
  busy: boolean;
  onRun: (parameters: Record<string, unknown>) => Promise<void>;
  onSignatureResult: (job: Job | null) => void;
}) {
  const [pages, setPages] = useState("1");
  const [ranges, setRanges] = useState("1");
  const [profile, setProfile] = useState("balanced");
  const [text, setText] = useState("GİZLİ");
  const [signer, setSigner] = useState("");
  const [manualUrl, setManualUrl] = useState<string | null>(null);
  const selectedTool = TOOLS.find((item) => item.id === tool)!;
  const pageValues = () => pages.split(",").map((value) => Number(value.trim())).filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (tool === "signature") {
      if (!document.latest_version) return;
      const created = await api<{ id: string }>("/signature-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey() },
        body: JSON.stringify({
          version_id: document.latest_version.id,
          signer: { display_name: signer },
          fields: [{ type: "signature", page_number: 1, x_pt: 72, y_pt: 72, width_pt: 180, height_pt: 48, required: true }],
        }),
      });
      const invited = await api<{ manual_url: string }>(`/signature-requests/${created.id}/invite`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey() },
      });
      setManualUrl(invited.manual_url);
      onSignatureResult(null);
      return;
    }
    const parameters: Record<string, unknown> = {};
    if (tool === "split") Object.assign(parameters, { mode: "range", ranges });
    if (tool === "reorder") Object.assign(parameters, { pages: pageValues() });
    if (tool === "rotate") Object.assign(parameters, { pages: pageValues(), degrees: 90 });
    if (tool === "compress") Object.assign(parameters, { profile });
    if (tool === "watermark") Object.assign(parameters, { text, opacity: 0.2, rotation: -35, font_size: 38, pages: [] });
    if (tool === "redact") Object.assign(parameters, { rectangles: [{ page_number: 1, x_pt: 72, y_pt: 72, width_pt: 180, height_pt: 48 }], remove_metadata: true });
    if (tool === "ocr") Object.assign(parameters, { languages: ["tur", "eng"], pages: [], deskew: true, text_layer_policy: "skip" });
    await onRun(parameters);
  }

  const blocked = tool === "merge" && mergeCount < 2 || tool === "signature" && !document.latest_version || tool === "office_to_pdf" && document.media_type === "application/pdf";
  return (
    <form className="tool-panel" onSubmit={(event) => void submit(event)}>
      <div className="tool-heading"><span className="tool-glyph">{selectedTool.glyph}</span><div><span className="eyebrow">Aktif araç</span><h3>{selectedTool.label}</h3></div></div>
      {tool === "merge" && <p>Soldaki kutulardan en az iki belge seç. Seçim sırası kütüphane sırasına göre korunur. <strong>{mergeCount} seçili</strong></p>}
      {tool === "split" && <label>Sayfa aralıkları<input value={ranges} onChange={(event) => setRanges(event.target.value)} placeholder="1-3,5,8-10" /></label>}
      {tool === "reorder" && <label>Yeni sayfa sırası<input value={pages} onChange={(event) => setPages(event.target.value)} placeholder="3,1,2" /></label>}
      {tool === "rotate" && <label>Döndürülecek sayfalar<input value={pages} onChange={(event) => setPages(event.target.value)} placeholder="1,3" /></label>}
      {tool === "compress" && <label>Profil<select value={profile} onChange={(event) => setProfile(event.target.value)}><option value="lossless">Kayıpsız</option><option value="balanced">Dengeli</option><option value="smallest">En küçük</option></select></label>}
      {tool === "watermark" && <label>Filigran metni<input value={text} onChange={(event) => setText(event.target.value)} /></label>}
      {tool === "redact" && <p>Varsayılan alan, 1. sayfada 72 × 72 pt başlangıcından kalıcı olarak rasterize edilir. Orijinal korunur; sonucu ayrıca gözle doğrula.</p>}
      {tool === "ocr" && <p>Türkçe + İngilizce metin katmanı yerel Tesseract ile oluşturulur. İnternet gerekmez.</p>}
      {tool === "office_to_pdf" && <p>DOCX, XLSX veya PPTX yerel LibreOffice ile izole profilde PDF’e çevrilir.</p>}
      {tool === "signature" && <><label>İmzalayan etiketi<input value={signer} onChange={(event) => setSigner(event.target.value)} placeholder="Ad Soyad" required /></label><p className="scope-inline">Bu akış nitelikli e-imza veya kimlik doğrulama değildir.</p>{manualUrl && <div className="manual-link"><code>{`${window.location.origin}${manualUrl}`}</code><button type="button" onClick={() => void navigator.clipboard.writeText(`${window.location.origin}${manualUrl}`)}>Kopyala</button></div>}</>}
      <button className="button primary wide" disabled={busy || blocked} type="submit">{busy ? "İşleniyor…" : blocked ? "Gerekli kaynağı seç" : `${selectedTool.label} işlemini başlat`}</button>
    </form>
  );
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  return <section className="audit"><div className="panel-heading"><h3>Append-only audit</h3><span>{events.length} olay</span></div>{events.map((event) => <div className="audit-row" key={event.id}><span className="audit-dot" /><div><strong>{event.event_type}</strong><small>{new Date(event.occurred_at).toLocaleString("tr-TR")}</small>{event.output_sha256 && <code>{shortHash(event.output_sha256)}</code>}</div></div>)}</section>;
}

function asApiError(error: unknown) {
  return error instanceof ApiError ? error : new ApiError("UNEXPECTED_ERROR", error instanceof Error ? error.message : "Beklenmeyen bir hata oluştu.");
}
