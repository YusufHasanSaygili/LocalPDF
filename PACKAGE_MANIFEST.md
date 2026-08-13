# PACKAGE_MANIFEST

## Paket dosyaları

| Dosya | Amaç | Hedef repodaki önerilen yer |
|---|---|---|
| `README.md` | Paketi ve okuma sırasını açıklar | Geçici olarak kök; uygulama README'sine dönüştürülür |
| `PROJECT_SPEC.md` | Ürün kapsamı ve davranışları | `docs/PROJECT_SPEC.md` |
| `ARCHITECTURE.md` | Bileşen ve veri akışı | `docs/ARCHITECTURE.md` |
| `DIRECTORY_STRUCTURE.md` | Repo iskeleti/sınırlar | `docs/DIRECTORY_STRUCTURE.md` |
| `DATA_MODEL.md` | PostgreSQL şeması/invariant'lar | `docs/DATA_MODEL.md` |
| `API_CONTRACT.md` | v1 HTTP sözleşmesi | `docs/API_CONTRACT.md` |
| `SLICES.md` | Sıralı uçtan uca teslim planı | `docs/SLICES.md` |
| `TASKS.md` | Task ID'li master checklist | `TASKS.md` veya `docs/TASKS.md` |
| `ACCEPTANCE_CRITERIA.md` | P0/P1 release kapıları | `docs/ACCEPTANCE_CRITERIA.md` |
| `TEST_PLAN.md` | Unit/integration/E2E/fault planı | `docs/TEST_PLAN.md` |
| `SECURITY_PRIVACY.md` | Tehdit modeli ve local privacy | `docs/SECURITY_PRIVACY.md` |
| `UX_STATES.md` | Empty/loading/error/success matrisi | `docs/UX_STATES.md` |
| `OPERATIONS_BACKUP.md` | Backup/restore/expiry runbook | `docs/OPERATIONS_BACKUP.md` |
| `DECISIONS.md` | Bağlayıcı ADR'ler | `docs/DECISIONS.md` |
| `EXCLUSIONS.md` | Bilinçli kapsam dışı maddeler | `docs/EXCLUSIONS.md` |
| `RISK_REGISTER.md` | Risk/mitigation kaydı | `docs/RISK_REGISTER.md` |
| `TRACEABILITY_MATRIX.md` | Requirement→slice→test izi | `docs/TRACEABILITY_MATRIX.md` |
| `GIT_WORKFLOW.md` | Commit/push düzeni | `docs/GIT_WORKFLOW.md` |
| `COMMANDS.md` | Kanonik ve gerçek komut kaydı | `COMMANDS.md` |
| `IMPLEMENTATION_PROMPT.md` | Coding agent başlangıç prompt'u | Kök veya proje dışı handoff |
| `.env.example` | Secret içermeyen config şablonu | Repo kökü |
| `.gitignore.example` | Uygulama `.gitignore` tabanı | İçeriği repo `.gitignore`'a aktarılır |

## Kurulum yöntemi

Bu paket plan/dokümantasyon teslimidir. Boş uygulama reposu açıldığında `.env.example` köke bırakılır; teknik belgeler yukarıdaki yerleşime taşınır. Uygulama kodu `SLICES.md` ve `TASKS.md` sırasıyla eklenir.

## Doküman önceliği

Çelişki halinde öncelik: kullanıcının güncel açık talebi → `DECISIONS.md` → `PROJECT_SPEC.md` → `ACCEPTANCE_CRITERIA.md` → `ARCHITECTURE.md` → diğer plan belgeleri. Değişiklik ADR ve traceability güncellemesi gerektirir.

## Teslim bütünlüğü

ZIP oluştururken bu klasörün kök adı `LocalPDF-Proje-Paketi` kalmalıdır. Paket açıldığında tüm dosyalar tek üst klasörde görünmeli; kullanıcının aynı masaüstü klasöründeki diğer dosyalar arşive alınmamalıdır.

