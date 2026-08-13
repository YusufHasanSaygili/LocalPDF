# COMMANDS — Kanonik komutlar ve final kayıt

Bu dosyanın ilk bölümü hedef komut sözleşmesidir. Uygulama tamamlanınca ikinci bölüm **gerçek çalıştırılan komutlarla** doldurulur; varsayılan örnekler başarı kanıtı sayılmaz.

## 1. İlk çalıştırma — tek komut

```powershell
docker compose up --build
```

Beklenen: migration tamamlanır; `web`, `api`, `worker`, `db` healthy/ready olur. Web `http://localhost:3000`, API `http://localhost:8000`.

## 2. Ortam hazırlama

Kalıcı/local secret değerlerini değiştirmek için:

```powershell
Copy-Item .env.example .env
```

`.env` oluşturmak first run için zorunlu tutulmamalıdır; Compose güvenli localhost geliştirme varsayılanlarıyla açılmalıdır. Public kullanım desteklenmez.

## 3. Doğrulama komutları

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
docker compose ps
docker compose down
git diff --check
git status --short
```

Repo root'ta `just`, `make` veya başka wrapper eklenebilir ama bu exact Docker Compose komutları dokümante ve çalışır kalmalıdır.

## 4. Backup/restore

```powershell
.\scripts\backup.ps1 -Destination "D:\LocalPDF-Backups"
.\scripts\restore.ps1 -Archive "D:\LocalPDF-Backups\<archive>" -Destination ".\data-restored"
```

Restore dolu hedefi reddetmelidir. Bash eşdeğerleri Linux/macOS için aynı semantiği taşır.

## 5. Slice Git kapanışı

```powershell
git status --short
git diff --check
git diff --stat
git add <slice-dosyalari>
git diff --cached --check
git diff --cached --stat
git commit -m "feat(scope): outcome"
git branch --show-current
git remote -v
git push -u origin <branch>
```

Push ancak remote tanımlı ve yetki varsa yapılır. Hata halinde force push veya credential'ı dosyaya yazma yoktur.

---

# FINAL EXECUTION RECORD — uygulama bitince doldur

## Ortam

- Tarih/saat (UTC): `2026-08-13T18:24:06Z`
- İşletim sistemi: `Microsoft Windows NT 10.0.22631.0`
- Docker sürümü: `CLI bulunamadı`
- Git branch: `feat/localpdf-implementation`
- Test edilen Git SHA: `703a2312aa447675ebff98387ad9349b14a620b9`
- Compose image/tag/digest özeti: `Doğrulanamadı; Docker CLI bu hostta kurulu değil`

## Çalıştırılan exact commands

| # | Exact command | Exit code | Süre | Sonuç/not |
|---|---|---:|---:|---|
| 1 | `uv run ruff check app tests ../../scripts` | 0 | <1 sn | Tüm kontroller geçti |
| 2 | `uv run pytest -q` | 0 | 2.78 sn | 12 passed, 1 skipped (native Poppler entegrasyonu) |
| 3 | `uv run mypy app` | 0 | ~3 sn | 30 source file, sorun yok |
| 4 | `uv run python -m compileall -q app migrations ../../scripts` | 0 | <1 sn | Python syntax smoke geçti |
| 5 | `npm run lint` (`apps/web`) | 0 | ~4 sn | ESLint temiz |
| 6 | `npm run typecheck` (`apps/web`) | 0 | ~3 sn | TypeScript strict temiz |
| 7 | `npm test` (`apps/web`) | 0 | 0.98 sn | 1 test geçti |
| 8 | `npm run build` (`apps/web`) | 0 | ~18 sn | Next.js 15 production build geçti |
| 9 | `npm audit` (`apps/web`) | 0 | <1 sn | 0 vulnerability |
| 10 | `npx playwright test --list` (`tests/e2e`) | 0 | 2.1 sn | 1 E2E test keşfedildi |
| 11 | `npm audit` (`tests/e2e`) | 0 | <1 sn | 0 vulnerability |
| 12 | `uv export --frozen --all-extras --no-hashes --output-file audit-requirements.tmp; uvx pip-audit -r audit-requirements.tmp` | 0 | 29.3 sn | Bilinen Python dependency açığı yok |
| 13 | `docker compose build` | 1 | <1 sn | `docker` komutu bu hostta bulunamadı |
| 14 | `git diff --check` | 0 | <1 sn | Whitespace hatası yok |
| 15 | `.\scripts\check-secrets.ps1` | 0 | <1 sn | Tracked secret veya private `.env` yok |

## Test özeti

- Backend unit/integration: `12 passed, 1 skipped`; native Poppler/DB/Compose integration Docker'a kaldı
- Frontend unit/component: `1 passed`
- Lint/typecheck: backend Ruff + mypy ve frontend ESLint + TypeScript başarılı
- E2E happy path: Playwright testi keşfedildi; gerçek browser run Docker yokluğu nedeniyle çalıştırılmadı
- Clean first run: Docker CLI bulunmadığı için çalıştırılmadı
- Offline smoke: Core code remote API içermez; gerçek Compose offline smoke çalıştırılmadı
- Backup/restore round-trip: Script syntax/validation hazır; Docker/PostgreSQL round-trip çalıştırılmadı

## Git teslimi

- Final `git status --short`: final docs commit sonrasında temiz olarak yeniden kontrol edilecek
- Push remote/branch: remote tanımlı değil / `feat/localpdf-implementation`
- Push sonucu: push yapılmadı; remote yok
- Son anlamlı commit'ler: `703a231 feat(web)`, `8c69926 feat(core)`, `5718e7a docs`

## Bilinen sınırlamalar / blokajlar

- Docker CLI yok: Compose build/first-run, PostgreSQL trigger testi, container tool integration, E2E ve backup/restore release kapıları bu hostta doğrulanamadı.
- Redaksiyon integration testi Windows'taki `.cmd` Poppler sarmalayıcısı native executable olmadığı için skip oldu; worker container gerçek `pdftoppm` içerir.
- FastAPI test client, upstream geçiş dönemi nedeniyle `httpx2` öneren tek bir deprecation warning üretiyor; test sonucunu etkilemiyor.
