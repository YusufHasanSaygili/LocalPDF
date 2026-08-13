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

- Tarih/saat (UTC): `TODO`
- İşletim sistemi: `TODO`
- Docker sürümü: `TODO`
- Git branch: `TODO`
- Git HEAD SHA: `TODO`
- Compose image/tag/digest özeti: `TODO`

## Çalıştırılan exact commands

| # | Exact command | Exit code | Süre | Sonuç/not |
|---|---|---:|---:|---|
| 1 | `TODO` |  |  |  |

## Test özeti

- Backend unit/integration: `TODO`
- Frontend unit/component: `TODO`
- Lint/typecheck: `TODO`
- E2E happy path: `TODO`
- Clean first run: `TODO`
- Offline smoke: `TODO`
- Backup/restore round-trip: `TODO`

## Git teslimi

- Final `git status --short`: `TODO`
- Push remote/branch: `TODO`
- Push sonucu: `TODO`
- Son anlamlı commit'ler: `TODO`

## Bilinen sınırlamalar / blokajlar

- `TODO`

