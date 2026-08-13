# DATA_MODEL

PostgreSQL tüm metadata, job ve audit kayıtlarının kaynağıdır. Zamanlar UTC `timestamptz`, kimlikler UUID, hash değerleri lowercase hex SHA-256 olarak saklanır. Şema Alembic migration'larıyla versionlanır.

## Temel tablolar

### `documents`

| Alan | Tür | Kural |
|---|---|---|
| `id` | uuid PK | Uygulama üretir |
| `display_name` | text | Normalize edilmiş kullanıcı adı |
| `safe_name` | text | Header/export için güvenli ad |
| `media_type` | text | İzinli listeden |
| `state` | enum | active, expired, deleted |
| `created_at` | timestamptz | UTC |
| `expires_at` | timestamptz null | Gelecek zaman veya null |
| `deleted_at` | timestamptz null | Tombstone |

### `originals`

| Alan | Tür | Kural |
|---|---|---|
| `id` | uuid PK | |
| `document_id` | uuid FK unique | Belge başına tek original |
| `relative_path` | text unique | Store root'a göre |
| `sha256` | char(64) | Index |
| `byte_size` | bigint | >= 0 |
| `page_count` | integer null | Office kaynağında null olabilir |
| `detected_features` | jsonb | encryption/forms/signatures/fonts |
| `created_at` | timestamptz | |

`originals` için uygulama katmanında update yoktur; DB trigger kritik alan update/delete'ini reddeder.

### `operations`

| Alan | Tür | Kural |
|---|---|---|
| `id` | uuid PK | |
| `document_id` | uuid FK null | Merge çok kaynaklı olabilir |
| `type` | enum | merge, split, reorder, rotate, compress, watermark, redact, ocr, office_to_pdf, signature_seal |
| `parameters` | jsonb | Şema sürümüyle doğrulanmış |
| `idempotency_key` | text unique | İstemci retry güvenliği |
| `created_at` | timestamptz | |

### `operation_inputs`

`operation_id`, `input_kind` (original/version), `input_id`, `position`, `sha256`. Merge sırası ve chain-of-custody için hash snapshot saklanır.

### `document_versions`

| Alan | Tür | Kural |
|---|---|---|
| `id` | uuid PK | |
| `document_id` | uuid FK | |
| `operation_id` | uuid FK | Üreten operasyon |
| `version_number` | integer | document ile unique |
| `relative_path` | text unique | |
| `sha256` | char(64) | |
| `byte_size` | bigint | |
| `page_count` | integer | > 0 |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz null | |
| `deleted_at` | timestamptz null | Fiziksel byte silinmiş olabilir |

### `jobs`

`id`, `operation_id`, `kind`, `state`, `payload`, `progress_percent`, `attempt_count`, `max_attempts`, `available_at`, `lease_owner`, `lease_expires_at`, `heartbeat_at`, `error_code`, `safe_error_message`, `created_at`, `started_at`, `finished_at`.

Index: `(state, available_at)`; claim transaction'ı `FOR UPDATE SKIP LOCKED` kullanır. Retry yalnız transient hata kodlarında ve idempotent handler'larda yapılır.

### `previews`

`id`, `version_or_original_id`, `source_kind`, `page_number`, `relative_path`, `width`, `height`, `sha256`, `state`, `created_at`. Kaynak + sayfa unique.

### `signature_requests`

`id`, `version_id`, `state` (draft/invited/viewed/consented/sealed/expired/cancelled), `consent_text_version`, `token_hash`, `token_expires_at`, `created_at`, `sealed_version_id`.

### `signature_fields`

`id`, `request_id`, `type`, `page_number`, `x_pt`, `y_pt`, `width_pt`, `height_pt`, `required`, `value_kind`. Koordinatlar sayfa MediaBox/CropBox sınırında doğrulanır.

### `signers`

`id`, `request_id`, `display_name`, `delivery_address` (opsiyonel/yerel), `status`, `consented_at`. Regulated identity alanı yoktur.

### `delivery_attempts`

`id`, `request_id`, `channel` (smtp/manual), `outcome` (sent/delivered/failed/manual), `provider_message_id` null, `safe_error`, `attempted_at`. Vendor zorunlu değildir.

### `events`

`id`, `occurred_at`, `event_type`, `aggregate_type`, `aggregate_id`, `actor_type`, `correlation_id`, `document_sha256` null, `output_sha256` null, `schema_version`, `payload` jsonb.

Append-only trigger:

- `UPDATE` reddedilir.
- `DELETE` reddedilir.
- Payload boyutu sınırlandırılır.
- Event silinmesi yerine ilgili aggregate için tombstone olayı eklenir.

## İlişkiler ve invariant'lar

- Document 1—1 Original.
- Document 1—N Version; `(document_id, version_number)` unique.
- Operation N—N input (join table) ve 1—N output version.
- Başarılı output'ın dosyası bulunmalı, hash'i eşleşmeli ve valid PDF açılabilmelidir.
- Deleted document'ın yeni operation'ı olamaz.
- Sealed signature request tekrar seal edilemez.
- Event satırındaki hash, olay anındaki immutable snapshot'tır.

## Migration stratejisi

- Her şema değişikliği ileri migration + mümkünse güvenli downgrade içerir.
- Production benzeri veri üzerinde destructive migration yoktur; add/backfill/switch düzeni izlenir.
- Event tablosu migration'ları payload schema version ile geriye uyumlu tutulur.
- Testte boş DB migration head'e çıkarılır ve downgrade/upgrade smoke testi yapılır.

