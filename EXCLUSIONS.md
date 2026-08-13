# EXCLUSIONS — Bilinçli olarak yapılmayacaklar

Bu sınırlar scope creep'i ve yanlış güvenlik/hukuk iddialarını önler.

## Kesin kapsam dışı

- Nitelikli, düzenlemeye tabi veya sertifika tabanlı elektronik imza (QES/PKI/PAdES güven hizmeti)
- Government ID, e-Devlet, passport, biometric, liveness veya KYC doğrulaması
- Elektronik imzanın hukuken bağlayıcı olduğuna dair garanti
- Tam Acrobat düzeyi PDF text/object/layout editing
- Enterprise document governance: RBAC, legal hold, DLP, e-discovery, policy engine, organization admin
- Kullanıcı hesabı, login, ekip/workspace, paylaşım izinleri
- Billing, subscription, trial, license server
- Telemetry, product analytics, remote crash reporting, advertising
- Hosted control plane, SaaS backend, vendor'a belge upload
- Public internet deployment hardening veya multi-tenant isolation
- Mobile native app
- PDF malware antivirus ürünü olma iddiası

## P0 dışında, ancak ileride ADR ile değerlendirilebilir

- SSE/WebSocket progress
- Password ile encrypted PDF açma
- Handwritten signature drawing biometrics
- Network share/NAS store
- S3-compatible storage
- Mobile responsive advanced editor
- Full-text library search
- Automatic cloud backup

Bu maddeler kullanıcı onayı ve yeni threat model olmadan eklenmez.

## Dil kuralları

Kullanma: “yasal imza”, “kimliği doğrulandı”, “resmî olarak geçerli”, “tam güvenli redaksiyon garantisi”, “silinen veri kurtarılamaz”.

Kullan: “signature-lite”, “açık rıza kaydı”, “final dosya hash'i”, “düşük riskli kişisel kullanım”, “uygulama store'undan silinir; backup/snapshot kopyaları ayrı yönetilir”.

