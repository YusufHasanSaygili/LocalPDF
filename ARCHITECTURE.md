# ARCHITECTURE

## 1. Genel yaklaşım

Modüler monolith + ayrı worker process kullanılır. Web, API, worker ve PostgreSQL Docker Compose ile yerelde ayağa kalkar. Metadata PostgreSQL'de, büyük dosya baytları bind-mounted kullanıcı dizininde saklanır. API request thread'i uzun dönüşüm çalıştırmaz; job tablosuna kayıt bırakır. Worker job'ları PostgreSQL `FOR UPDATE SKIP LOCKED` ile sahiplenir.

```text
Browser :3000
   |
   v
Next.js 15 web  ---- same-origin/API URL ----> FastAPI :8000
                                                |       |
                                                |       +--> Local file store
                                                v
                                           PostgreSQL
                                                ^
                                                |
                                   Python worker process
                                   pikepdf / LibreOffice
                                   Tesseract / Poppler
```

## 2. Compose servisleri

| Servis | Görev | Kalıcı veri |
|---|---|---|
| `web` | Next.js UI, istemci durumları | Yok |
| `api` | FastAPI, upload/download, metadata, job oluşturma | Store bind mount read/write |
| `worker` | PDF/Office/OCR/preview işleri | Store bind mount read/write |
| `db` | PostgreSQL | Named volume veya kullanıcı tanımlı host path |

API ve worker aynı Python image'ından farklı command ile başlatılabilir. LibreOffice, Tesseract ve Poppler bu image içinde sürümü pinlenmiş sistem paketleridir.

## 3. Katmanlar

### Web

- `app/`: Next.js App Router sayfaları ve server boundary'leri
- `features/`: upload, library, editor, operation forms, signature-lite
- `components/`: ortak durum bileşenleri, warning banner, progress, toast
- `lib/api`: typed fetch client, error decoder, polling/backoff
- `lib/validation`: istemci şemaları; API doğrulaması otoritedir

### API

- `api/routes`: ince HTTP controller'ları
- `application/services`: use-case orchestration
- `domain`: entity, enum, invariant ve error kodları
- `infrastructure/db`: SQLAlchemy 2.x/Alembic repository'leri
- `infrastructure/storage`: path üretimi, atomik yazma, hashing
- `infrastructure/tools`: pikepdf, LibreOffice, Tesseract, Poppler adapter'ları

### Worker

- PostgreSQL job claim loop
- Lease/heartbeat ve stale job recovery
- Operation handler registry
- Per-job temp workspace
- Output validation + atomic publish
- Progress ve event üretimi

## 4. Veri depolama düzeni

```text
${LOCAL_DATA_DIR}/
  originals/<document_uuid>/<sha256>.<ext>
  outputs/<document_uuid>/v000001/<output_uuid>.pdf
  previews/<version_uuid>/page-000001.webp
  exports/<export_uuid>/bundle.zip
  backups/<timestamp>/localpdf-backup.tar.zst
  tmp/<job_uuid>/
```

- `originals` içindeki dosya create-once'dır; uygulama güncelleme endpoint'i sunmaz.
- DB kayıtları mutlak host path değil, store root'a göre göreli path tutar.
- Output version numarası transaction içinde doküman bazında artar.
- Aynı filesystem üzerindeki temp-to-final rename atomiktir.
- `tmp` başlangıçta ve job sonunda orphan cleanup'a tabidir.

## 5. Upload akışı

1. Stream multipart içeriği limitli buffer ile temp dosyaya alınır.
2. Stream sırasında SHA-256 ve byte count hesaplanır.
3. Dosya adı sanitize edilir; magic byte ve izinli içerik türü doğrulanır.
4. PDF ise pikepdf ile güvenli açma ve feature scan yapılır.
5. DB transaction document/original kayıtlarını oluşturur.
6. Temp dosya immutable hedefe atomik taşınır.
7. `document.uploaded` event'i append edilir.
8. PDF preview job'ı enqueue edilir.

DB commit ile dosya taşıma arasındaki crash için reconciliation job, orphan dosya ve missing-file kayıtlarını event ile raporlar.

## 6. Dönüşüm akışı ve durum makinesi

```text
queued -> running -> validating -> succeeded
   |         |            |
   +-------> failed <------+
   +-------> cancelled (yalnız başlamadan veya handler güvenliyse)
```

- Job payload JSONB'dir ancak `operation_type` bazında Pydantic discriminated union ile doğrulanır.
- Worker job'ı lease ile claim eder; heartbeat süresi aşarsa sınırlı retry yapılır.
- Her handler yalnız kendi temp dizinine yazar.
- Üretilen PDF pikepdf ile yeniden açılır; beklenen sayfa sayısı/invariant kontrol edilir.
- Başarıda output/version/event tek DB transaction'da kaydedilir.
- Idempotency key aynı isteğin çift tıklanmasıyla iki çıktı üretmesini engeller.

## 7. Append-only event log

- Uygulama rolüne `INSERT` ve `SELECT` verilir; `UPDATE/DELETE` verilmez.
- DB trigger event satırlarında update/delete'i reddeder.
- Event alanları: id (UUIDv7/UUID), occurred_at UTC, type, aggregate id, actor type, correlation id, document hash, output hash, payload schema version, minimal JSON payload.
- Hassas link token'ları ve dosya içeriği payload'a yazılmaz.
- Export JSONL sırası `(occurred_at, id)` ile deterministiktir.

## 8. Signature-lite mimarisi

- Invite token DB'de plaintext değil hash olarak tutulur; token expiry vardır.
- Consent kaydı; signer label, document hash, consent text version, accepted_at, IP kaydı varsayılan kapalı, user-agent kaydı varsayılan kapalıdır.
- Field coordinates PDF point sisteminde saklanır; UI viewport koordinatı server tarafında doğrulanmış dönüşümle çevrilir.
- Completion handler alanları görünür içerik olarak uygular, PDF'i flatten eder, final hash üretir ve `signature.sealed` event'i yazar.
- SMTP adapter opsiyoneldir. Yapılandırma yoksa API `manual` delivery oluşturur; bütün ana akış çalışır.

## 9. Hata modeli

Standart hata gövdesi:

```json
{
  "error": {
    "code": "PDF_ENCRYPTED",
    "message": "Bu PDF parola ile korunuyor.",
    "recoverable": true,
    "correlation_id": "...",
    "details": {"allowed_action": "upload_unlocked_copy"}
  }
}
```

Beklenen domain hataları 4xx, sistem/araç unavailable hataları 503, beklenmeyen hatalar içerik sızdırmayan 500 döner. Worker hata detayının kullanıcıya güvenli özeti ile teknik log ayrıdır.

## 10. Güven sınırları

- Uygulama localhost'a bind edilir; public deployment desteklenmez.
- Upload içeriği düşmanca kabul edilir.
- LibreOffice makro çalıştırmadan, izole profil ve timeout ile çağrılır.
- Download endpoint'i yalnız DB'de kayıtlı relative path'i storage adapter üzerinden çözer.
- Symlink takip edilmez; çözülmüş path store root altında doğrulanır.

## 11. Gözlemlenebilirlik (telemetri olmadan)

- Yalnız yerel structured log: timestamp, level, service, correlation id, job id, event type.
- Sağlık: `/health` process canlılığı; `/ready` DB/store/araç hazır oluşu.
- Admin dashboard yoktur; local status sayfası servis sürümlerini ve kullanılabilir araçları gösterir.
- Log dışa gönderilmez; analytics SDK eklenmez.

## 12. Yedekleme ve restore

Backup script kısa süreli tutarlı snapshot alır: PostgreSQL dump + store manifest + dosyalar. Manifest her dosyanın relative path, byte size ve SHA-256 değerini içerir. Restore boş hedefe yapılır, path/hash kontrol edilir, DB restore edilir ve reconciliation taraması çalışır. Ayrıntı `OPERATIONS_BACKUP.md` içindedir.

