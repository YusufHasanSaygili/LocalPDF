# SLICES — Uçtan uca geliştirme planı

## Kullanım kuralı

Slice'lar sırayla uygulanır. Her slice kullanıcıya görünen veya altyapıda doğrulanabilen tek bir sonuç bırakır. “Bitti” demek için slice testleri, lint/typecheck ve kabul kriterleri geçmelidir. Her büyük slice sonunda aşağıdaki Git kapanışı **ayrı görevdir**:

1. `git status --short` ile yalnız ilgili değişiklikleri gözden geçir.
2. Slice'ta belirtilen test/lint/typecheck komutlarını çalıştır.
3. `git diff --check` ve secret taraması yap.
4. `git add` ile yalnız slice dosyalarını stage et.
5. Conventional Commit biçiminde anlamlı commit oluştur.
6. Remote ayarlıysa mevcut feature branch'i `git push -u origin <branch>` ile push et.
7. Push sonucunu ve gerçek çalıştırılan komutları teslim notuna yaz.

Push/remote yetkisi yoksa force push yapılmaz; commit yerelde korunur ve blokaj açıkça raporlanır. GitHub aktivitesi için anlamsız “activity” commit'leri üretilmez; her slice bir veya birkaç bağımsız, yeşil commit'e bölünür.

---

## S00 — Repo foundation ve tek komutlu first run

**Amaç:** Boş repoda sabit stack, Compose, health endpoint ve web shell ayağa kalksın.

**Çıktılar:** Next.js 15 TypeScript app, Python 3.12 FastAPI app, PostgreSQL, worker process, Dockerfiles, Compose, `.env.example`, gitignore, Alembic başlangıcı, low-stakes warning.

**Görevler:**

- Repo dizinlerini `DIRECTORY_STRUCTURE.md` ile oluştur.
- Sürümleri lockfile/pyproject ile pinle; image tag'lerini floating bırakma.
- Compose healthcheck ve dependency readiness ekle.
- API `/health`, `/ready`, `/system/capabilities`; web home/empty state ekle.
- Migration'ları API başlamadan idempotent one-shot service ile çalıştır.
- `.env` yoksa güvenli local varsayılanlarla first run çalışsın; secret gerekiyorsa generate edilip host'a yazılmasın, kullanıcı `.env` ile kalıcılaştırabilsin.
- README'de yalnız doğrulanmış `docker compose up --build` başlangıcını yaz.

**Doğrulama:** Compose build; API unit smoke; web lint/typecheck; curl health; secret dosyalarının Git dışında oluştuğunu kontrol.

**Git kapanışı:** `chore: bootstrap localpdf stack` commit'i; status/diff/test/lint; ilgili dosyalara `git add`; commit; remote varsa push.

---

## S01 — Storage, veri modeli, event log ve job çekirdeği

**Amaç:** Immutable original, versioned output, append-only event ve PostgreSQL job leasing temeli.

**Çıktılar:** Alembic tabloları/trigger'ları, storage adapter, SHA-256/atomic write, job claim/heartbeat/retry, reconciliation.

**Görevler:**

- `DATA_MODEL.md` tablolarını migration ile oluştur.
- Event UPDATE/DELETE DB trigger testini yaz.
- Safe relative-path resolver ve symlink/root escape testlerini yaz.
- Stream hashing, atomic publish ve read-only original API'sini uygula.
- `FOR UPDATE SKIP LOCKED` job claim, lease ve stale recovery uygula.
- Worker kapanışında job'ı tutarlı state'e getir.

**Doğrulama:** Migration smoke; event immutability integration; storage property/edge tests; iki worker concurrency testi; crash/retry testi.

**Git kapanışı:** Mantıksal olarak `feat(storage): ...` ve `feat(worker): ...` commit'lerine bölünebilir; her commit öncesi test/lint, stage review ve sonra remote push.

---

## S02 — Upload, kütüphane, preview ve risk uyarıları

**Amaç:** Kullanıcı PDF yükleyip orijinali ve progressive sayfa önizlemelerini görebilsin.

**Çıktılar:** Multipart upload, filename/MIME/limit doğrulama, library UI, pikepdf feature scan, Poppler preview job, tüm UI durumları.

**Görevler:**

- Upload stream'ini boyut limitli ve hash'li uygula.
- PDF magic byte + pikepdf parse; Office türlerini ayrı policy ile doğrula.
- Encryption/form/signature/font warning sınıflandırmasını ekle.
- Preview job ile page WebP üret; first-page-first sıralaması kullan.
- Library/detail ekranına empty/loading/success/recoverable error ekle.
- Original indirme header ve filename testlerini ekle.

**Doğrulama:** Bozuk/şifreli/oversize/sahte uzantı fixture testleri; preview page count; upload UI testi; manuel olarak 1, 50+ sayfalı PDF.

**Git kapanışı:** `feat(library): add immutable uploads and previews`; API+web test/lint/typecheck; `git diff --check`; stage, commit, push.

---

## S03 — Merge ve split

**Amaç:** İlk tam PDF transformation döngüsü kullanıcıya teslim edilsin.

**Çıktılar:** Merge sıralaması, split range parser/modları, çoklu çıktı ZIP, version/output/event kayıtları, progress ve download.

**Görevler:**

- Merge handler ve input hash snapshot'larını uygula.
- Split range grammar ve bounds doğrulamasını uygula.
- Multi-output operation için transaction ve deterministic ZIP manifest ekle.
- UI'da ordering/range form, warning confirmation ve job sonucu göster.
- Output validation ve page-count invariant testlerini yaz.

**Doğrulama:** Golden/sentetik PDF merge-split testleri; invalid range table tests; çift tıklama idempotency; output hash/event doğrulama.

**Git kapanışı:** `feat(pdf): add merge and split workflows`; focused backend + frontend test/lint; stage review; commit; push.

---

## S04 — Reorder ve rotate

**Amaç:** Thumbnail editor üzerinde sayfa düzenleme.

**Çıktılar:** Accessible drag/reorder + keyboard alternatifi, rotate selection, server validation, yeni PDF version.

**Görevler:**

- Permutation invariant ve duplicate/missing page hatalarını uygula.
- Rotate 90/180/270 ve page box davranışını test et.
- UI undo-before-submit, selection ve preview state'lerini ekle.
- Büyük belgede render performansı için virtualized grid veya pagination uygula.

**Doğrulama:** 1/çok sayfa, mixed rotation, invalid permutation; keyboard accessibility; hash/version/event.

**Git kapanışı:** `feat(editor): add reorder and rotate`; test/lint/typecheck; diff/secret check; add; commit; push.

---

## S05 — Compress ve watermark

**Amaç:** Boyut optimizasyonu ve görünür filigran üretimi.

**Çıktılar:** Üç compression profile, before/after raporu, text watermark controls, deterministic placement.

**Görevler:**

- pikepdf lossless optimizasyonunu uygula; balanced/smallest için açık kalite politikası tanımla ve container araçlarını sabitle.
- Sonuç daha büyükse warning fakat valid output davranışını uygula.
- Watermark coordinate/opacity/font fallback adapter'ını uygula.
- Risk banner ve düşük çözünürlüklü draft preview ekle.

**Doğrulama:** Boyut raporu aritmetiği; sayfa sayısı; watermark placement snapshot; görünmez/boş parametre retleri; signed/form PDF warning.

**Git kapanışı:** `feat(pdf): add compression and watermark`; focused tests + lint/typecheck; stage; commit; push.

---

## S06 — Kalıcı redaksiyon

**Amaç:** Seçilen alanın yalnız üstünü kapatmak yerine içerikten kalıcı biçimde çıkarıldığı güvenli redaksiyon.

**Çıktılar:** Rectangle editor, PDF point conversion, redact handler, optional metadata scrub, post-redaction verification uyarısı.

**Görevler:**

- CropBox/rotation dikkate alan coordinate conversion yaz.
- Rectangle bounds, zero-area ve page index validation ekle.
- İçerik kaldırma ve appearance uygulamasını pikepdf tabanlı güvenli pipeline ile yap; yetersiz PDF yapılarında işlemi engelle.
- Redakte edilmiş metnin çıkarım testinde bulunmadığını doğrula; raster/görsel içerik için manuel doğrulama uyarısı ekle.
- Audit payload'a alanların tam metnini değil sayfa ve coordinate özetini yaz.

**Doğrulama:** Text content removal, metadata option, rotated page coordinates, malicious rectangle payload, reopen validation.

**Git kapanışı:** `feat(redaction): add permanent area redaction`; güvenlik odaklı testler + full lint; stage review; commit; push.

---

## S07 — OCR

**Amaç:** Taranmış PDF'i yerel olarak aranabilir PDF'e dönüştürmek.

**Çıktılar:** Tesseract language capability, page selection, deskew, progress, searchable output, unavailable-language UX.

**Görevler:**

- Tool readiness ve kurulu dil listesi endpoint'ini bağla.
- OCR subprocess'i argüman listesi, resource/timeout limitleri ve temp profile ile çalıştır.
- Text-layer zaten varsa policy (`skip|force`) uygula.
- UI dil/page/deskew formu ve uzun iş progress'ini ekle.

**Doğrulama:** Küçük tarama fixture'ında metin arama; eksik dil; timeout; cancel; offline execution; original immutability.

**Git kapanışı:** `feat(ocr): add local searchable PDF workflow`; OCR integration + lint/typecheck; add; commit; push.

---

## S08 — Office-to-PDF

**Amaç:** DOCX/XLSX/PPTX kaynaklarını LibreOffice headless ile yerelde PDF'e çevirmek.

**Çıktılar:** Office upload policy, isolated LibreOffice adapter, timeout/unavailable handling, layout/font warning, output preview.

**Görevler:**

- Macro execution disabled ve benzersiz user profile ile subprocess yaz.
- Allowlist input extension + magic/MIME eşleşmesi uygula.
- Output discovery'yi kullanıcı filename'ına bağlı olmadan güvenli yap.
- Font substitution ve spreadsheet pagination warning'lerini UI'a ekle.

**Doğrulama:** Üç Office fixture; timeout/exit nonzero; filename spaces/unicode; no output; process cleanup; valid PDF reopen.

**Git kapanışı:** `feat(convert): add local Office to PDF`; container integration + lint/typecheck; diff review; commit; push.

---

## S09 — Signature-lite consent ve hash sealing

**Amaç:** Düşük riskli, açıkça sınırlandırılmış imza alanı/consent/final hash akışı.

**Çıktılar:** Field placement, signer/davet, manual fallback, consent text version, flatten/seal, delivery event'leri, prominent disclaimer.

**Görevler:**

- Token generate/hash/expiry ve log redaction uygula.
- Field coordinate server validation ve required field checks ekle.
- SMTP adapter'ı opsiyonel yap; unavailable iken manual link üret.
- Consent ekranında document hash, metin sürümü, açık checkbox ve low-stakes warning göster.
- Seal job sonrası final hash/event/audit receipt üret.
- Qualified signature veya identity iddiası yapan metin olmadığını content test ile koru.

**Doğrulama:** Token expiry/reuse; consent required; seal idempotency; SMTP success/failure/manual; final hash; event sequence; privacy fields.

**Git kapanışı:** `feat(signature-lite): add consent and hash sealing`; security/integration/UI testleri + lint; add; commit; push.

---

## S10 — Expiry, download, deletion, export, backup/restore

**Amaç:** Kullanıcı verisinin tam yerel yaşam döngüsü ve taşınabilirliği.

**Çıktılar:** Expiry policy, scheduled cleanup, two-step delete, tombstone, document export, backup/restore scripts ve manifest verification.

**Görevler:**

- Expiry state transition ve fiziksel purge policy'sini uygula.
- Delete confirmation, active-job conflict ve idempotent cleanup ekle.
- Export ZIP'e original/versions/audit/manifest koy.
- PostgreSQL dump + store manifest backup; empty-target restore ve hash verify yaz.
- UI'da veri konumu, disk kullanımı, export/delete/backup sonuçlarını göster.

**Doğrulama:** Fake clock expiry; missing file reconciliation; delete race; ZIP traversal testi; backup-restore round-trip; hash mismatch abort.

**Git kapanışı:** `feat(lifecycle): add expiry export deletion and backup`; full integration + script checks; stage; commit; push.

---

## S11 — Dayanıklılık, validation, güvenlik ve tüm UX durumları

**Amaç:** Kötü girişler ve unavailable araçlar karşısında veri kaybetmeden anlaşılır davranış.

**Çıktılar:** Merkezi error map, retry/cancel, disk-full/DB/tool unavailable durumları, rate/concurrency limit, accessibility ve warning standardizasyonu.

**Görevler:**

- Pydantic payload union ve TypeScript form schema parity testleri ekle.
- Safe filename corpus testleri yaz.
- Storage quota/preflight, temp cleanup ve disk full error path ekle.
- DB/LibreOffice/Tesseract/SMTP unavailable senaryolarını UI component testleriyle kapsa.
- Focus management, keyboard use, contrast ve live progress semantics düzelt.

**Doğrulama:** Fault injection; recoverable/unrecoverable state matrix; API contract test; accessibility scan; local log secret test.

**Git kapanışı:** `fix(resilience): harden validation and recovery states`; tüm unit/integration + web lint/typecheck; add; commit; push.

---

## S12 — E2E happy path, temiz kurulum, dokümantasyon ve release adayı

**Amaç:** Ürünü temiz ortamda doğrulayıp auditable şekilde teslim etmek.

**E2E happy path:** Uygulamayı aç → iki PDF yükle → preview bekle → sırayı belirleyip merge et → output indir → hash/event görünümünü doğrula → export ZIP al.

**Görevler:**

- Playwright E2E'yi deterministic fixture ve job wait helper ile yaz.
- Tüm migration'ları boş DB'de çalıştır.
- Temiz clone/Compose first run'ı gerçek komutla doğrula.
- README setup, architecture, permissions, data location, backup, restore, warning ve exclusions bölümlerini güncelle.
- SBOM/dependency lisans özeti ve image vulnerability çıktısını değerlendir; secrets olmadığını doğrula.
- `COMMANDS.md` final execution record alanını gerçek komut/sonuç/tarih ile doldur.
- P0 acceptance checklist'i iki kişi yoksa self-review + ikinci temiz run ile kapat.

**Doğrulama:** Full backend/web/E2E; Compose stop/start persistence; backup restore; offline smoke; no network vendor call incelemesi.

**Git kapanışı:** `test(e2e): verify localpdf happy path` ve `docs: finalize local-first release guide`; her commit öncesi ilgili test/lint; `git add`; commit; remote varsa push; final `git status` temiz olmalı.

---

## S13 — Son kabul ve teslim raporu

Kod değişikliği beklenmez; yalnız doğrulama ve kanıt toplama slice'ıdır. `ACCEPTANCE_CRITERIA.md` P0 maddelerini, test raporlarını, exact command kayıtlarını, image/tag sürümlerini, known limitations ve varsa push blokajını tek teslim özetinde kapat. Düzeltme gerekirse ilgili önceki slice'a dön ve yeni anlamlı fix commit'i oluştur.

