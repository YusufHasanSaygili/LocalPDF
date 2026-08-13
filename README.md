# LocalPDF

LocalPDF; PDF ve Office belgelerini üçüncü taraf bir belge servisine göndermeden, kendi bilgisayarınızda işleyen tek kullanıcılı bir uygulamadır. Orijinal dosya create-once depoda korunur; her başarılı işlem yeni bir sürüm, SHA-256 ve append-only audit olayı üretir.

> LocalPDF düşük riskli kişisel kullanım içindir. Signature-lite özelliği nitelikli/düzenlemeye tabi elektronik imza, sertifika tabanlı imza veya kimlik doğrulama sağlamaz.

## Tek komutla çalıştırma

Gerekenler: Docker Desktop ve Compose v2. Repo kökünde:

```powershell
docker compose up --build
```

Ardından:

- Web: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/ready`
- OpenAPI: `http://localhost:8000/docs`

`.env` zorunlu değildir. Kalıcı yerel ayarları değiştirmek için:

```powershell
Copy-Item .env.example .env
```

Servisler varsayılan olarak yalnız `127.0.0.1` üzerinde yayınlanır. Public internet deployment ve multi-user isolation desteklenmez.

## Uygulanan akışlar

- PDF/DOCX/XLSX/PPTX yükleme; uzantı + magic/content doğrulaması
- Immutable original, güvenli relative path, stream SHA-256 ve atomik çıktı yayını
- PostgreSQL `SKIP LOCKED` job queue, lease/heartbeat, retry ve stale recovery
- Progressive WebP önizleme ve form/font/dijital imza risk uyarıları
- Merge, range/every-N/single-page split ve hash manifestli ZIP
- Reorder, rotate, üç compression profili ve boyut raporu
- Metin filigranı
- Kalıcı redaksiyon: seçili alanların raster pipeline ile içerikten çıkarılması; yalnız overlay çıktı yayımlanmaz
- Yerel Tesseract OCR ve izole LibreOffice Office-to-PDF
- Signature-lite: alan doğrulama, hash'lenmiş tek kullanımlık token, açık rıza sürümü, manual/SMTP teslim sonucu, flatten ve final hash
- Expiry state, iki aşamalı silme, document ZIP export ve deterministik audit JSONL
- PostgreSQL dump + dosya/hash manifestli backup ve boş hedefe doğrulamalı restore staging

## Mimari

```text
Browser → Next.js 15 → FastAPI → PostgreSQL
                         ↓            ↑
                    local store ← worker
                    pikepdf / Poppler / Tesseract / LibreOffice
```

`api` uzun PDF işlerini çalıştırmaz; doğrulanmış operation ve job kaydı oluşturur. `worker`, işi kendi geçici dizininde işler, PDF'i pikepdf ile yeniden açar, hash'ler ve aynı filesystem üzerinde atomik rename ile yayınlar. Event ve original satırlarında PostgreSQL mutation trigger'ları `UPDATE/DELETE` işlemini reddeder.

Yerel dosya düzeni:

```text
data/
  originals/<document-id>/<sha256>.<ext>
  outputs/<document-id>/v000001/<output-id>.pdf
  previews/<source-id>/page-000001.webp
  exports/<job-id>/*.zip
  tmp/<job-id>/
```

`data/`, `.env`, backup'lar, gerçek belgeler ve generated preview'lar Git'e girmez. Uygulama telemetry, analytics, remote font/CDN veya vendor belge API'si içermez. SMTP yalnız kullanıcı `.env` içinde açıkça etkinleştirirse kullanılır; aksi halde signature-lite manuel bağlantıyla çalışır.

## Doğrulama

```powershell
docker compose build
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm test
docker compose up -d
docker compose run --rm e2e npm test
docker compose down
```

Docker olmadan focused geliştirme kontrolleri:

```powershell
cd services/api
uv sync --python 3.12 --all-extras
uv run pytest -q
uv run ruff check .
uv run mypy app

cd ../../apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

## Backup ve restore

Uygulama çalışırken PostgreSQL dump ve store snapshot'ı almak:

```powershell
.\scripts\backup.ps1 -Destination "D:\LocalPDF-Backups"
```

Restore aktif verinin üzerine yazmaz. Önce stack'i durdurun, sonra yeni ve boş hedef kullanın:

```powershell
docker compose down
.\scripts\restore.ps1 -Archive "D:\LocalPDF-Backups\localpdf-....zip" -Destination ".\data-restored"
```

Restore script'i ZIP traversal/symlink, manifest sürümü, DB dump hash'i ve her store dosyasının boyut/hash değerini doğrular. Ardından ayrı bir Compose project adıyla yeni PostgreSQL volume oluşturur, dump'ı bu boş veritabanına yükler ve `restore-info.json` içine geçiş ayarlarını yazar. Mevcut data veya DB volume otomatik silinmez.

## Güvenlik sınırları

- Upload içeriği düşmanca kabul edilir; filename hiçbir disk path'inde kullanılmaz.
- Şifreli PDF açılmaz; kullanıcıdan kilidi kaldırılmış kopya istenir.
- Subprocess çağrıları argument listesi, allowlist ve timeout kullanır; shell interpolation yoktur.
- Redaksiyon görüntü içeriği için ayrıca görsel kontrol gerektirir.
- Uygulama store'undan silme, SSD wear-leveling, filesystem snapshot, OneDrive geçmişi veya daha önce alınmış backup kopyalarını geri getirilemez biçimde silmeyi garanti etmez.
- Host işletim sistemi veya Docker daemon ele geçirilmişse uygulama gizlilik garantisi veremez.

Tam kapsam ve bağlayıcı kararlar için [PROJECT_SPEC.md](PROJECT_SPEC.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md), [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md) ve [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) dosyalarına bakın.

## Bilinen doğrulama sınırı

Bu çalışma ortamında Docker CLI bulunmadığı için gerçek Compose first-run, PostgreSQL trigger integration, container içi LibreOffice/Tesseract/Poppler, Playwright happy path ve backup/restore round-trip burada çalıştırılamadı. İlgili image, migration, test ve scriptler repoda hazırdır; release kapısı olarak Docker bulunan makinede yukarıdaki komutlar çalıştırılmalıdır.
