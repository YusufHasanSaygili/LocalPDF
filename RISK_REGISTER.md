# RISK_REGISTER

| ID | Risk | Etki | Olasılık | Önleme/tespit | Owner slice |
|---|---|---|---|---|---|
| R01 | Original yanlışlıkla overwrite | Kritik veri kaybı | Düşük/Orta | Create-once store, read-only API, hash/mtime test | S01 |
| R02 | DB kaydı ve filesystem ayrışır | Yüksek | Orta | Atomic publish, transaction sınırı, reconciliation | S01 |
| R03 | Redaction yalnız overlay kalır | Kritik gizlilik | Orta | Content removal + extraction post-check + fail closed | S06 |
| R04 | PDF bomb/çok karmaşık dosya kaynak tüketir | Yüksek | Orta | Boyut/sayfa/time/memory/concurrency limit | S02/S11 |
| R05 | LibreOffice makro/profile etkisi | Yüksek | Düşük/Orta | Macro disabled, isolated profile, non-root, timeout | S08 |
| R06 | Mevcut dijital imza dönüşümle bozulur | Yüksek | Yüksek | Feature scan + blocking confirmation + new version | S02+ |
| R07 | Font substitution layout değiştirir | Orta | Yüksek | Warning, preview, pinned font set | S05/S08 |
| R08 | Event log değiştirilebilir | Yüksek audit kaybı | Düşük/Orta | DB trigger/privilege integration test | S01 |
| R09 | Token log/DB'de sızar | Yüksek | Orta | Hash storage, redaction, tests, expiry | S09 |
| R10 | Signature-lite hukuki imza sanılır | Yüksek | Orta | Prominent scope warning, forbidden-copy test | S09 |
| R11 | SMTP yokluğu ana akışı bozar | Orta | Yüksek | Manual fallback + delivery outcome | S09 |
| R12 | Disk dolar, yarım output görünür | Yüksek | Orta | Preflight, temp write, atomic rename, cleanup | S11 |
| R13 | Backup var ama restore çalışmaz | Kritik | Orta | Her release round-trip, manifest hashes | S10/S12 |
| R14 | OneDrive/data sync kilitleri | Orta | Orta (Windows) | Retryable atomic errors, local data path recommendation | S10/S11 |
| R15 | Worker crash aynı işi iki kere yayımlar | Yüksek | Orta | Lease + idempotency + unique constraint | S01 |
| R16 | Unsafe filename/header injection | Yüksek | Orta | Safe ASCII fallback/RFC5987/corpus tests | S02 |
| R17 | Dependency/image açığı | Yüksek | Orta | Pinned versions, review scan, rebuild cadence | S12 |
| R18 | Scope büyümesi first run'ı geciktirir | Orta | Yüksek | Ordered slices, exclusions, P0/P1 gates | Tümü |

Risk kapanışı yalnız “test var” ile değil; ilgili test adı/çıktısı ve kabul kriteri kanıtıyla yapılır.

