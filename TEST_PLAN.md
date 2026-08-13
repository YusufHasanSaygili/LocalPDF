# TEST_PLAN

## 1. Test piramidi

- **Unit:** range parser, filename sanitizer, coordinate math, hashing, validation, error mapping, event payload.
- **Integration:** gerçek PostgreSQL, filesystem temp store, pikepdf, Tesseract, LibreOffice ve Poppler adapter'ları.
- **Component/UI:** operation forms, warning confirmation, job progress ve bütün UX durumları.
- **E2E:** gerçek Compose stack üzerinde Playwright ile tek ana happy path; az sayıda yüksek değerli failure path.
- **Operational:** temiz kurulum, restart persistence, backup/restore, offline ve disk pressure.

Unit testte pikepdf davranışını aşırı mock'lama; küçük sentetik PDF fixture'larıyla gerçek parse/write yapılır. External process failure'ları adapter sınırında kontrollü fake executable veya container integration ile test edilir.

## 2. Fixture seti

`tests/fixtures` içinde programatik veya lisansı açık küçük dosyalar:

- 1, 3 ve 10 sayfalı, sayfa numarası görünür PDF
- Rotated CropBox/MediaBox PDF
- AcroForm içeren PDF
- İmza dictionary'si taşıyan örnek (gerçek kişisel imza yok)
- Şifreli PDF (test parolası repo belgesinde açıkça test-only)
- Bozuk/truncated PDF ve sahte `.pdf` uzantılı text
- Görsel tabanlı kısa OCR PDF (`eng`, varsa `tur`)
- Filigran/redaction için bilinen metin koordinatlı PDF
- Küçük DOCX, XLSX, PPTX; font bağımlılığı düşük
- Unicode, boşluk, çok uzun ve Windows reserved-name filename corpus'u

Fixture hash'leri manifest ile sabitlenir. Gerçek kullanıcı belgesi commit edilmez.

## 3. Core focused test matrisi

| Alan | En az testler |
|---|---|
| Immutable upload | hash/mtime aynı, duplicate hash, atomic failure cleanup |
| Merge | sıra, toplam page count, metadata warning, encrypted input |
| Split | aralık, tek sayfa, every-N, overlap policy, bounds, ZIP manifest |
| Reorder | permutation, duplicate/missing page, 1-page no-op policy |
| Rotate | 90/180/270, selected-only, existing rotation |
| Compress | üç profil, valid reopen, size math, larger-output warning |
| Watermark | placement, opacity, rotation, page scope, unicode fallback |
| Redact | extracted text absent, rotated coordinate, metadata scrub, overlay-only guard |
| OCR | searchable text, missing language, timeout, already-has-text policy |
| Office | DOCX/XLSX/PPTX, timeout, nonzero exit, no output, unicode name |
| Preview | page count/order, progressive ready, render failure |
| Signature-lite | token hash/expiry/reuse, consent, seal hash, delivery outcomes |
| Lifecycle | expiry clock, delete race/idempotency, export paths, restore hash mismatch |
| Audit | append-only trigger, event ordering, hash snapshot, JSONL determinism |

## 4. Güvenlik testleri

- Filename: `../`, absolute Windows/Unix, alternate data stream `:`, NUL, control chars, `CON`, `NUL`, trailing dot/space, bidi controls.
- Archive: ZIP slip ve symlink entry; export yalnız uygulama ürettiği allowlist path'leri kullanır.
- Download: arbitrary id/path yok; resolved path root altında; symlink reddi.
- Subprocess: kullanıcı girdisi executable/shell string'e giremez; timeout ve kill process tree.
- Token: URL token log redaction, DB hash, constant-time compare, expiry/replay.
- Log: `.env` secret, SMTP password, document bytes/text ve invite token bulunmadığını test et.
- Resource: upload limit, page limit, job concurrency, decompression/complex PDF timeout, disk preflight.

## 5. Fault injection

| Arıza | Beklenen sonuç |
|---|---|
| PostgreSQL operation sırasında gider | Job/output tutarsız yayımlanmaz; retry/reconciliation |
| Disk full | `STORAGE_FULL`, temp cleanup, original korunur |
| Worker kill | Lease expire sonrası idempotent retry |
| LibreOffice yok | capability false + 503 recoverable; diğer PDF işleri çalışır |
| Tesseract dili yok | desteklenen dillerle recoverable hata |
| Poppler render fail | belge kullanılabilir; preview error/retry |
| SMTP yok/yanıt vermiyor | manual fallback veya failed delivery event; seal akışı yerel sürer |
| Tarayıcı refresh | Job id ile progress yeniden bağlanır |

## 6. E2E happy path (P0)

Tek test mümkün olduğunca kullanıcı davranışını kapsar:

1. Temiz stack'i başlat.
2. Kütüphane empty state ve low-stakes warning'i doğrula.
3. İki sentetik PDF yükle.
4. Her biri için preview ve hash bilgisini bekle.
5. Merge aracına ekle, ikinci dosyayı birinci sıraya taşı.
6. Warning varsa onayla ve operation başlat.
7. Progress sonrası success state, page count ve version 1'i doğrula.
8. Çıktıyı indir; test tarafında SHA-256'yı UI/API hash'iyle karşılaştır.
9. Audit görünümünde upload ve merge event'lerini doğrula.
10. Document export ZIP al; manifest ve hash'leri doğrula.

Test fixed sleep kullanmaz; API/job state veya görünür UI condition bekler. Retry yalnız bilinen browser timing için sınırlı ve raporlu olabilir.

## 7. Manuel keşif kontrolü

- 100+ sayfalı PDF'de preview/progress ve UI responsiveness.
- Font/form/signature/encryption warning metninin anlaşılır oluşu.
- Compression kalite profillerinin gözle karşılaştırması.
- Watermark ve redaction coordinate doğruluğu farklı page rotation'larında.
- Windows Unicode filename download/export.
- Uygulama internet bağlantısı kapalıyken temel akış.
- Veri konumu, backup ve silme uyarılarının bulunabilirliği.

## 8. Test komutları — hedef sözleşme

Gerçek repo script adları farklılaşırsa README ve CI ile birlikte güncellenir; tek kanonik komut seti korunur:

```powershell
docker compose build
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm test -- --run
docker compose up -d
docker compose run --rm e2e npm test
docker compose down
```

Test raporunda exact command, UTC tarih, image/git SHA, exit code ve başarısız test isimleri tutulur.

## 9. Release kapısı

- P0 testlerin tamamı yeşil.
- Flaky test quarantine edilerek gizlenmez; kök neden çözülür.
- Coverage yüzdesi tek başına hedef değildir; bütün core operation happy/failure invariant'ları kapsanır.
- Backup/restore ve temiz first-run en az bir kez gerçek Docker volume/data path ile çalıştırılır.
- Test sonrası `git status --short` generated data göstermemelidir.

