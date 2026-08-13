# DIRECTORY_STRUCTURE — Hedef repo

```text
localpdf/
  .env.example
  .gitignore
  AGENTS.md
  README.md
  docker-compose.yml
  package.json                  # yalnız root yardımcı scriptleri gerekiyorsa
  docs/
    PROJECT_SPEC.md
    ARCHITECTURE.md
    DATA_MODEL.md
    API_CONTRACT.md
    SECURITY_PRIVACY.md
    UX_STATES.md
    OPERATIONS_BACKUP.md
    TEST_PLAN.md
    ACCEPTANCE_CRITERIA.md
    DECISIONS.md
    EXCLUSIONS.md
  apps/
    web/
      Dockerfile
      package.json
      next.config.ts
      tsconfig.json
      app/
      components/
      features/
      lib/
      tests/
  services/
    api/
      Dockerfile
      pyproject.toml
      alembic.ini
      app/
        main.py
        settings.py
        api/routes/
        application/services/
        domain/
        infrastructure/db/
        infrastructure/storage/
        infrastructure/tools/
        worker/
      migrations/
      tests/
  scripts/
    backup.ps1
    backup.sh
    restore.ps1
    restore.sh
    verify-tools.py
  tests/
    e2e/
      package.json
      playwright.config.ts
      specs/
      fixtures/
  data/                         # gitignored; bind mount default
    .gitkeep                    # isteğe bağlı, veri değil
```

## Sınırlar

- Web, PDF binary'sini işlemeye çalışmaz; yalnız API'ye gönderir ve preview gösterir.
- API route'ları doğrudan pikepdf/LibreOffice çağırmaz; application service ve job üretir.
- Domain katmanı framework import etmez.
- Tool adapter'ları subprocess ve pikepdf ayrıntılarını tek yerde kapsüller.
- Test fixture'ları küçük, sentetik ve lisans açısından güvenli olmalıdır.
- `data/`, `.env`, backup arşivleri, gerçek belgeler ve generated previews Git'e girmez.

## Dosya sahipliği

| Alan | Sahip |
|---|---|
| HTTP sözleşmesi | `services/api/app/api` + `API_CONTRACT.md` |
| İş kuralları | `domain` / `application` |
| Disk path ve atomicity | `infrastructure/storage` |
| PDF/Office/OCR | `infrastructure/tools` |
| Job leasing/retry | `worker` |
| UI durumları | `apps/web/features` |
| E2E | `tests/e2e` |

