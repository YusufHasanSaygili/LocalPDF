# IMPLEMENTATION_PROMPT — Coding agent başlangıç talimatı

Aşağıdaki metni boş repo ile çalışan coding agent'a verin:

```text
Bu repoda LocalPDF uygulamasını uygula. Önce kökteki README.md ve docs altındaki bütün bağlayıcı belgeleri oku; özellikle PROJECT_SPEC.md, ARCHITECTURE.md, DECISIONS.md, SLICES.md, TASKS.md, ACCEPTANCE_CRITERIA.md, TEST_PLAN.md, SECURITY_PRIVACY.md ve GIT_WORKFLOW.md.

Teknoloji yığını kesindir: Next.js 15, TypeScript, Python 3.12, FastAPI, pikepdf, LibreOffice headless ve PostgreSQL. Alternatif stack, vendor belge API'si, hesap, billing, telemetry, analytics veya hosted control plane ekleme.

SLICES.md sırasıyla ilerle. Bir slice'a başlarken TASKS.md maddelerini durumlandır; küçük, uçtan uca ve test edilebilir değişiklikler yap. Original dosyaları asla yerinde değiştirme; her operation yeni versioned output, SHA-256 ve append-only event üretmeli. Uzun işler PostgreSQL job worker'da çalışmalı. Dosya adlarını/path'leri güvenli işle ve tüm subprocess çağrılarını shell interpolation olmadan timeout ile yap.

Her büyük slice sonunda ilgili focused testleri, backend/frontend lint ve typecheck'i, `git diff --check` ve secret kontrolünü çalıştır. Yalnız ilgili dosyaları `git add` ile stage et, anlamlı Conventional Commit oluştur ve remote ayarlı/yetkiliyse mevcut branch'i push et. Push mümkün değilse zorlamadan exact hatayı raporla. Kullanıcıya ait ilgisiz değişiklikleri geri alma veya commit etme.

Tek komut first run sözleşmesini koru: `docker compose up --build`. `.env.example` gönder, credential commit etme. UI'ın empty/loading/progress/success/recoverable error/blocked durumlarını ve font/form/signature/encryption uyarılarını eksiksiz yap.

Signature-lite özelliğinin nitelikli/düzenlemeye tabi e-imza veya kimlik doğrulama olmadığını her ilgili ekranda belirt. Consent kaydı ve final hash sealing yap; SMTP yokken manual fallback kullan. Redaction yalnız overlay olamaz; content removal doğrulanamıyorsa fail closed.

Bitirmeden önce en az bir Playwright happy path'i, temiz Compose first run, restart persistence, offline smoke ve backup/restore round-trip çalıştır. README'yi gerçek davranışla güncelle ve COMMANDS.md FINAL EXECUTION RECORD bölümüne tam komutları, exit code'ları, tarihi, platformu, git SHA'yı ve push sonucunu yaz. Son yanıtta değişenleri, testleri, exact commands'i ve bilinen sınırlamaları listele.
```

## Agent'a çalışma sırasında verilecek kısa komut

```text
Sıradaki tamamlanmamış slice'ı uygula. İlgili acceptance kriterleri geçmeden sonraki slice'a geçme. Slice Git kapanış görevini de tamamla ve kanıtları raporla.
```

