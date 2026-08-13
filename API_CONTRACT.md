# API_CONTRACT — v1

Base path: `/api/v1`. JSON alanları snake_case. Zamanlar ISO-8601 UTC. Binary upload/download haricinde `application/json` kullanılır. Liste endpoint'leri cursor pagination kullanır.

## Ortak kurallar

- Her response `X-Correlation-ID` döndürür.
- Mutating operation endpoint'leri `Idempotency-Key` header kabul eder ve gerektirir.
- Dosya yolları hiçbir response'ta dönmez; opaque id ve API URL döner.
- Hata gövdesi `ARCHITECTURE.md` içindeki standart biçimdedir.
- Job response: `id`, `state`, `progress_percent`, `operation_id`, `result_ids`, `error`.

## Sistem

| Method | Path | Amaç |
|---|---|---|
| GET | `/health` | Process liveness |
| GET | `/ready` | DB, store ve tool readiness |
| GET | `/system/capabilities` | LibreOffice/Tesseract dilleri/limitler |

## Dokümanlar

| Method | Path | Amaç |
|---|---|---|
| POST | `/documents` | Multipart upload; original oluşturur |
| GET | `/documents` | Kütüphane listesi |
| GET | `/documents/{id}` | Document, original, version ve warning özeti |
| PATCH | `/documents/{id}/expiry` | Expiry ayarla/kaldır |
| DELETE | `/documents/{id}` | Onay token'ıyla delete job üret |
| GET | `/documents/{id}/export` | Export job oluştur/durum döndür |

Upload alanları: `file`, opsiyonel `expires_at`. Response 202 ise preview job bağlantısı da bulunur.

## Önizleme ve indirme

| Method | Path | Amaç |
|---|---|---|
| GET | `/sources/{kind}/{id}/previews` | Hazır/progress sayfaları |
| GET | `/previews/{id}/content` | Thumbnail stream |
| GET | `/originals/{id}/download` | Original download |
| GET | `/versions/{id}/download` | Version download |

`kind`: `original` veya `version`. Download response güvenli ASCII fallback + RFC 5987 filename, `X-Content-Type-Options: nosniff`, private/no-store cache policy taşır.

## Operasyon oluşturma

`POST /operations` discriminated body kabul eder:

```json
{
  "type": "rotate",
  "inputs": [{"kind": "version", "id": "..."}],
  "parameters": {"pages": [1, 3], "degrees": 90}
}
```

Response `202 Accepted`: operation + job URL.

### Parametre özetleri

- `merge`: sıralı en az iki input.
- `split`: `mode=range|every_n|single_pages`, doğrulanmış range expression.
- `reorder`: her sayfayı tam bir kez içeren 1-based permutation.
- `rotate`: sayfa listesi ve `90|180|270`.
- `compress`: `lossless|balanced|smallest`.
- `watermark`: text, opacity, rotation, anchor/x-y, pages.
- `redact`: page ve PDF-point rectangle listesi, `remove_metadata`.
- `ocr`: languages, pages, deskew.
- `office_to_pdf`: Office original id.
- `signature_seal`: signature request id.

## Job'lar

| Method | Path | Amaç |
|---|---|---|
| GET | `/jobs/{id}` | Progress ve sonuç |
| POST | `/jobs/{id}/retry` | Yalnız recoverable failed job |
| POST | `/jobs/{id}/cancel` | Güvenli state'lerde iptal |

Polling önerisi: ilk 2 saniye 500 ms, sonra exponential backoff maksimum 3 saniye; sayfa görünmezse polling durur. Sonraki aşamada SSE eklenebilir fakat P0 değildir.

## Signature-lite

| Method | Path | Amaç |
|---|---|---|
| POST | `/signature-requests` | Draft + fields + signer oluştur |
| POST | `/signature-requests/{id}/invite` | SMTP veya manual delivery |
| GET | `/sign/{token}` | Public-local consent görünümü |
| POST | `/sign/{token}/consent` | Consent kaydı ve seal job |
| GET | `/signature-requests/{id}` | Durum ve audit özeti |
| POST | `/signature-requests/{id}/cancel` | Seal öncesi iptal |

Token yalnız URL'de bir kez gösterilir; DB hash saklar. Token log ve event payload'ına yazılmaz.

## Audit ve backup

| Method | Path | Amaç |
|---|---|---|
| GET | `/documents/{id}/events` | Belge event'leri |
| GET | `/documents/{id}/audit-export` | JSONL export |
| POST | `/maintenance/backups` | Yerel backup job; UI'dan açık onay |
| GET | `/maintenance/backups/{id}` | Backup manifest/durum |

Restore HTTP üzerinden sunulmaz; yanlış hedefe overwrite riskini azaltmak için yalnız documented local script/CLI ile yapılır.

## Ana hata kodları

`FILE_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `FILENAME_INVALID`, `PDF_CORRUPT`, `PDF_ENCRYPTED`, `PAGE_RANGE_INVALID`, `PAGE_OUT_OF_BOUNDS`, `FEATURE_MAY_CHANGE`, `TOOL_UNAVAILABLE`, `OCR_LANGUAGE_UNAVAILABLE`, `OFFICE_CONVERSION_TIMEOUT`, `OUTPUT_VALIDATION_FAILED`, `JOB_NOT_RETRYABLE`, `TOKEN_INVALID_OR_EXPIRED`, `CONSENT_REQUIRED`, `DOCUMENT_EXPIRED`, `DOCUMENT_DELETED`, `STORAGE_FULL`, `DATABASE_UNAVAILABLE`.

