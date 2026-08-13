"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { Job } from "@/lib/types";

type ConsentView = {
  request_id: string;
  document_hash: string;
  signer_label: string;
  consent_text: string;
  consent_text_version: string;
  disclaimer: string;
};

export default function ConsentPage() {
  const params = useParams<{ token: string }>();
  const [view, setView] = useState<ConsentView | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<ConsentView>(`/sign/${encodeURIComponent(params.token)}`)
      .then(setView)
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : "Davet bağlantısı açılamadı."));
  }, [params.token]);

  async function consent() {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ job_id: string }>(`/sign/${encodeURIComponent(params.token)}/consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accepted: true }),
      });
      for (;;) {
        const current = await api<Job>(`/jobs/${result.job_id}`);
        setJob(current);
        if (["succeeded", "failed"].includes(current.state)) break;
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Rıza kaydedilemedi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="consent-shell">
      <section className="consent-card">
        <div className="brand"><span className="brand-mark">L</span><span>LocalPDF</span></div>
        {error && <div className="consent-error" role="alert"><strong>Devam edilemiyor</strong><p>{error}</p></div>}
        {!view && !error && <div className="consent-loading">Davet doğrulanıyor…</div>}
        {view && job?.state !== "succeeded" && (
          <>
            <span className="eyebrow">Signature-lite rıza kaydı</span>
            <h1>Belgeyi gözden geçir</h1>
            <p className="consent-disclaimer">△ {view.disclaimer}</p>
            <dl className="consent-details">
              <div><dt>İmzalayan etiketi</dt><dd>{view.signer_label}</dd></div>
              <div><dt>Belge SHA-256</dt><dd><code>{view.document_hash}</code></dd></div>
              <div><dt>Rıza metni sürümü</dt><dd>{view.consent_text_version}</dd></div>
            </dl>
            <div className="consent-text"><strong>Açık rıza metni</strong><p>{view.consent_text}</p></div>
            <label className="consent-check"><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} /><span>Belge hash’ini ve rıza metnini gördüm; alanların belgeye uygulanmasını kabul ediyorum.</span></label>
            {job && <div className="consent-progress" aria-live="polite">Mühürleniyor · %{job.progress_percent}</div>}
            <button className="button primary wide" disabled={!accepted || busy} onClick={() => void consent()}>{busy ? "Final dosya hazırlanıyor…" : "Rızayı kaydet ve hash ile mühürle"}</button>
          </>
        )}
        {job?.state === "succeeded" && (
          <div className="consent-success"><span>✓</span><h1>Belge mühürlendi</h1><p>Final görünüm belgeye uygulandı ve yeni SHA-256 üretildi.</p><code>{String(job.result?.final_sha256 ?? "")}</code><small>Bu kayıt nitelikli elektronik imza veya kimlik doğrulama değildir.</small></div>
        )}
      </section>
    </main>
  );
}

