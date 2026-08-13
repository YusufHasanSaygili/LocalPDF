# TASKS — Master görev şeması

Durum işaretleri: `[ ]` bekliyor, `[-]` sürüyor, `[x]` kanıtla tamamlandı. Her task PR/commit açıklamasında ID'siyle anılır. “Kod yazıldı” tek başına tamamlanma değildir; test ve kabul kanıtı gerekir.

## S00 Foundation

- [ ] `S00-T01` Repo dizinlerini ve sahiplik sınırlarını oluştur.
- [ ] `S00-T02` Next.js 15 + TypeScript strict kur; lint/typecheck/test scriptlerini ekle.
- [ ] `S00-T03` Python 3.12 + FastAPI + pikepdf projesini ve locked dependencies'i kur.
- [ ] `S00-T04` PostgreSQL ve Alembic başlangıç migration altyapısını kur.
- [ ] `S00-T05` API/worker image'ına LibreOffice headless, Tesseract ve Poppler ekle; sürümleri capabilities'te göster.
- [ ] `S00-T06` Compose health/readiness ve data bind mount'larını oluştur.
- [ ] `S00-T07` `.env.example`, `.gitignore`, local-only bind ve low-stakes warning ekle.
- [ ] `S00-T08` Tek komut first run smoke testini yaz/doğrula.
- [ ] `S00-T09` Test + lint + typecheck + `git diff --check` çalıştır.
- [ ] `S00-T10` Slice dosyalarını stage et, anlamlı commit oluştur, remote varsa push et ve sonucu kaydet.

## S01 Core persistence

- [ ] `S01-T01` Document/original/version/operation/input şemasını migration ile oluştur.
- [ ] `S01-T02` Job lease, heartbeat, retry ve stale recovery şemasını/worker'ını ekle.
- [ ] `S01-T03` Append-only event tablo, DB izinleri ve reject trigger'larını ekle.
- [ ] `S01-T04` Safe storage resolver, stream SHA-256, atomic write/publish ekle.
- [ ] `S01-T05` Output reopen/invariant validation ve reconciliation job'ını ekle.
- [ ] `S01-T06` Concurrency, immutability ve crash integration testlerini çalıştır.
- [ ] `S01-T07` Lint/typecheck/diff/secret kontrolünden sonra stage, commit ve push yap.

## S02 Intake ve preview

- [ ] `S02-T01` Upload limit, magic/MIME, filename ve hash doğrulamasını uygula.
- [ ] `S02-T02` PDF feature scan ve warning taxonomy'yi uygula.
- [ ] `S02-T03` Progressive Poppler preview job ve preview endpoint'lerini ekle.
- [ ] `S02-T04` Library/detail/download UI ve durum bileşenlerini ekle.
- [ ] `S02-T05` Malicious/invalid upload ve preview test corpus'unu çalıştır.
- [ ] `S02-T06` Test/lint/typecheck sonrası stage, commit ve push yap.

## S03 Merge/split

- [ ] `S03-T01` Merge domain validation ve pikepdf handler yaz.
- [ ] `S03-T02` Split range parser ile üç split modunu yaz.
- [ ] `S03-T03` Çoklu output transaction, ZIP manifest ve audit event'lerini yaz.
- [ ] `S03-T04` Merge/split formları, sıralama, progress, success/error ekranlarını yaz.
- [ ] `S03-T05` Page count/hash/idempotency focused testlerini çalıştır.
- [ ] `S03-T06` Lint/typecheck/diff sonrası stage, commit ve push yap.

## S04 Reorder/rotate

- [ ] `S04-T01` Permutation ve rotate handler/invariant'larını yaz.
- [ ] `S04-T02` Accessible thumbnail editor ve keyboard ordering ekle.
- [ ] `S04-T03` Undo-before-submit, selection ve large-document UI performansını ekle.
- [ ] `S04-T04` Mixed rotation/permutation/a11y testlerini çalıştır.
- [ ] `S04-T05` Test/lint/typecheck sonrası stage, commit ve push yap.

## S05 Compress/watermark

- [ ] `S05-T01` Üç compression profile ve before/after raporu yaz.
- [ ] `S05-T02` Watermark placement/opacity/page-scope handler yaz.
- [ ] `S05-T03` Risk warnings ve draft preview UI ekle.
- [ ] `S05-T04` File-size math, reopen, snapshot ve parameter testlerini çalıştır.
- [ ] `S05-T05` Test/lint/typecheck sonrası stage, commit ve push yap.

## S06 Redaction

- [ ] `S06-T01` PDF point/canvas coordinate dönüşümü ve bounds doğrulaması yaz.
- [ ] `S06-T02` Permanent content removal + appearance + metadata option uygula.
- [ ] `S06-T03` Rectangle editor ve mandatory verification warning ekle.
- [ ] `S06-T04` Text absence, rotated page, malicious payload ve reopen testlerini çalıştır.
- [ ] `S06-T05` Güvenlik review + lint/test sonrası stage, commit ve push yap.

## S07 OCR

- [ ] `S07-T01` Tesseract readiness/language detection ve adapter yaz.
- [ ] `S07-T02` Page/language/deskew/text-layer policy ve job progress ekle.
- [ ] `S07-T03` OCR UI ve graceful missing-language/timeout durumlarını ekle.
- [ ] `S07-T04` Searchable output/offline/timeout/original immutability testlerini çalıştır.
- [ ] `S07-T05` Test/lint/typecheck sonrası stage, commit ve push yap.

## S08 Office conversion

- [ ] `S08-T01` Office magic/MIME allowlist ve immutable intake ekle.
- [ ] `S08-T02` Isolated-profile LibreOffice adapter, timeout ve cleanup yaz.
- [ ] `S08-T03` Font/layout/form warning ve conversion UI ekle.
- [ ] `S08-T04` DOCX/XLSX/PPTX/unicode filename/failure testlerini çalıştır.
- [ ] `S08-T05` Container integration + lint sonrası stage, commit ve push yap.

## S09 Signature-lite

- [ ] `S09-T01` Request/signer/field/delivery/consent şemasını ekle.
- [ ] `S09-T02` Secure token hash/expiry/reuse protection ekle.
- [ ] `S09-T03` Field editor ve coordinate server validation yaz.
- [ ] `S09-T04` SMTP optional adapter + manual fallback + delivery event'lerini yaz.
- [ ] `S09-T05` Consent version/hash display ve seal/flatten/final hash yaz.
- [ ] `S09-T06` Regulated-signature exclusion ve prominent warning content testlerini yaz.
- [ ] `S09-T07` Security/integration/UI testleri sonrası stage, commit ve push yap.

## S10 Lifecycle

- [ ] `S10-T01` Expiry scheduling/state/purge policy uygula.
- [ ] `S10-T02` Two-step delete, active job conflict ve tombstone event uygula.
- [ ] `S10-T03` Safe download ve portable document export ZIP yaz.
- [ ] `S10-T04` Backup manifest/DB dump/store archive scriptlerini yaz.
- [ ] `S10-T05` Empty-target restore, hash verify ve reconciliation yaz.
- [ ] `S10-T06` Fake clock/delete race/ZIP traversal/backup round-trip testlerini çalıştır.
- [ ] `S10-T07` Test/lint/script checks sonrası stage, commit ve push yap.

## S11 Hardening

- [ ] `S11-T01` API/UI validation parity ve stable error map tamamla.
- [ ] `S11-T02` Filename/path/symlink/command injection corpus testlerini tamamla.
- [ ] `S11-T03` Disk full, DB/tool/SMTP unavailable ve retry/cancel akışlarını tamamla.
- [ ] `S11-T04` Temp cleanup, concurrency/resource limit ve safe local logs tamamla.
- [ ] `S11-T05` Keyboard/focus/contrast/live-region accessibility düzeltmelerini tamamla.
- [ ] `S11-T06` Fault injection + full lint/typecheck sonrası stage, commit ve push yap.

## S12 Release doğrulama

- [ ] `S12-T01` Playwright merge happy path yaz ve stabilize et.
- [ ] `S12-T02` Boş DB migration ve temiz Compose first run yap.
- [ ] `S12-T03` Restart persistence, offline smoke ve backup/restore run yap.
- [ ] `S12-T04` README permissions/data location/backup/warnings/exclusions tamamla.
- [ ] `S12-T05` Full test/lint/typecheck/E2E ve secret/dependency kontrollerini çalıştır.
- [ ] `S12-T06` `COMMANDS.md` actual execution record'u doldur.
- [ ] `S12-T07` Release docs ve E2E commitlerini anlamlı şekilde stage/commit/push yap.

## S13 Teslim

- [ ] `S13-T01` Tüm P0 acceptance kriterlerini kanıt linki/log adıyla kapat.
- [ ] `S13-T02` Known limitations ve kalan P1/P2 işlerini listele.
- [ ] `S13-T03` Exact command + exit code + tarih + platform teslim raporunu üret.
- [ ] `S13-T04` Final `git status --short`, branch ve son commit hash'ini kaydet.
- [ ] `S13-T05` Remote varsa son push'u doğrula; yoksa kullanıcıya tek açık blokaj olarak bildir.

