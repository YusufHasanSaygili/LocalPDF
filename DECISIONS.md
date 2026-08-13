# DECISIONS — Bağlayıcı teknik kararlar

## ADR-001 — Sabit stack

Next.js 15 + TypeScript, Python 3.12 + FastAPI, pikepdf, LibreOffice headless ve PostgreSQL kullanılır. Alternatif framework, database veya vendor PDF API önerilmez. Tesseract ve Poppler yalnız OCR/preview için container içi yardımcı executable'dır; ana stack'i değiştirmez.

## ADR-002 — Local-first ve kullanıcıya ait store

Dosya baytları local bind mount'ta, metadata PostgreSQL'de. Cloud object store veya hosted control plane yoktur. Varsayılan bind localhost'tur.

## ADR-003 — Original immutable, output versioned

Original create-once path'te SHA-256 adıyla saklanır. Hiçbir transformation in-place değildir. Her output document-scoped monotonic version + UUID path alır.

## ADR-004 — PostgreSQL job queue, Redis yok

Ek servis azaltmak için jobs tablosu, `SKIP LOCKED`, lease ve heartbeat kullanılır. Handler'lar idempotent tasarlanır. Uzun işler API process'inde çalışmaz.

## ADR-005 — Filesystem bytes, DB metadata

PDF/Office blob'ları PostgreSQL bytea olarak tutulmaz. DB relative path/hash/size/invariant taşır. Backup iki alanı birlikte snapshot eder.

## ADR-006 — Atomic publish

Output temp dizinde üretilir; yeniden açılır, invariant ve hash kontrol edilir, aynı filesystem içinde atomik rename ile final olur. Doğrulanmayan output kullanıcıya sunulmaz.

## ADR-007 — Append-only event enforcement DB'de

Yalnız uygulama niyetine güvenilmez; trigger ve DB privileges update/delete'i engeller. Düzeltme yeni event ile yapılır.

## ADR-008 — Polling önce, SSE sonra

P0 job progress typed polling + backoff ile yapılır. SSE/WebSocket zorunlu değildir. Bu, first run ve hata ayıklamayı sade tutar.

## ADR-009 — Encryption P0'da açılmaz

Uygulama parola toplamaz/saklamaz. Encrypted PDF blocked state ile kilidi kaldırılmış kopya ister.

## ADR-010 — Redaction güvenli değilse fail closed

Yalnız overlay kabul edilmez. Content removal/post-check desteklenemeyen PDF yapısında operation başarısız olur; yanıltıcı çıktı yayımlanmaz.

## ADR-011 — Signature-lite açıkça düşük riskli

Alan yerleşimi, consent, delivery outcome ve final hash vardır; PKI/QES, identity verification veya hukuki geçerlilik garantisi yoktur. Terminoloji ve UI test ile korunur.

## ADR-012 — SMTP opsiyonel

SMTP bir kolaylıktır, core dependency değildir. Yokluğunda manual invite link ve `manual` delivery event'i kullanılır.

## ADR-013 — Restore yalnız boş hedefe

In-place restore veri ezme riskinden dolayı yoktur. Restore yeni dizin/volume'a yapılır, doğrulanır, sonra kullanıcı konfigürasyonla geçiş yapar.

## ADR-014 — Telemetri yok, local structured log var

Analytics/crash vendor yoktur. Sorun çözme için kullanıcı cihazında structured log ve correlation id tutulur; belge içeriği/secret redacted'dır.

## Karar değişikliği yöntemi

Bağlayıcı kararı değiştirmek için yeni `ADR-0xx` eklenir: bağlam, karar, alternatifler, veri/güvenlik/migration etkisi ve geri dönüş planı. Eski karar silinmez; `Superseded by` ile işaretlenir.

