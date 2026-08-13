# SECURITY_PRIVACY

## Tehdit modeli

Korunan varlıklar: orijinal ve çıktı belge baytları, document/output hash'leri, consent kayıtları, invite token'ları, SMTP credential'ları, PostgreSQL verisi ve backup'lar.

Varsayılan güven sınırı: kişisel bilgisayar + localhost. Upload edilen PDF/Office dosyası düşmanca kabul edilir. Host işletim sistemi veya Docker daemon tamamen ele geçirilmişse uygulama gizlilik garantisi veremez. Public internet exposure ve multi-user isolation kapsam dışıdır.

## Privacy ilkeleri

- Belge işleme yerel container'larda yapılır; belge baytı vendor'a gönderilmez.
- Telemetry, analytics, crash reporter, hosted control plane veya remote font/CDN yoktur.
- Uygulama internet olmadan core akışı çalıştırır.
- Yalnız kullanıcının açık SMTP yapılandırması davet tesliminde dış bağlantı yapabilir; UI bunu işlemden önce belirtir.
- Local log belge metni, token, credential veya raw request body içermez.
- IP/user-agent consent metadata varsayılan kapalıdır; P0'da toplanmaz.

## Dosya güvenliği

- Stream upload, byte limit dolunca hemen kesilir.
- Uzantı, declared MIME ve magic byte birlikte değerlendirilir.
- Kullanıcı adı sadece display metadata'dır; disk path UUID/hash tabanlıdır.
- `Path.resolve` eşdeğeriyle root containment doğrulanır; symlink takip edilmez.
- Original create-once; çıktılar yeni version path; temp dosya final adla görünmez.
- Permission hedefi: data dizini yalnız mevcut kullanıcı/Docker service erişimi. README Windows/Linux örneklerini verir.
- Download `nosniff`, private/no-store ve güvenli Content-Disposition kullanır.

## Subprocess güvenliği

- `shell=True`, string interpolation veya kullanıcı kontrollü executable yoktur.
- LibreOffice benzersiz `UserInstallation`, macro disabled, headless/no-restore ve timeout ile çalışır.
- Tesseract/Poppler allowlist parametre alır.
- Process tree timeout/cancel'da sonlandırılır; temp profile temizlenir.
- Container non-root kullanıcı, dropped capabilities, no-new-privileges ve read-only base filesystem hedeflenir; yalnız store/temp gerekli mount'lar writable'dır.
- Varsayılan egress kapatma Docker Compose'ta platform uyumluluğu ölçüsünde uygulanır/dokümante edilir; SMTP etkinse yalnız açık kullanım beklenir.

## Secret yönetimi

- Bütün secret'lar `.env` içindedir; `.env.example` yalnız placeholder taşır.
- `.env`, `*.pem`, backup, database dump, invite URL ve `data/` gitignored.
- Commit öncesi secret scanner veya en azından staged diff kontrolü zorunludur.
- Token 256-bit CSPRNG ile üretilir, DB'de SHA-256/HMAC hash saklanır, log redaction middleware'i uygulanır.
- PostgreSQL password production-like local kullanımda değiştirilir; örnek secret gerçek sayılmaz.

## PDF özellik riskleri

- Encryption: parola toplama/decrypt P0 kapsamında yok; kullanıcı unlocked copy yükler.
- Form: dönüşüm form field'larını flatten/değiştirebilir; warning.
- Digital signature: herhangi bir byte değişikliği mevcut imzayı geçersiz kılabilir; blocking confirmation.
- Fonts: Office/annotation/watermark font substitution olabilir; warning + preview.
- Redaction: overlay güvenli değildir; content removal doğrulaması başarısızsa output yayımlanmaz.
- Metadata: redaction'da optional scrub; kullanıcının seçimi audit event'te.

## Event ve audit mahremiyeti

Event append-only olması her şeyi kaydetmek anlamına gelmez. Payload allowlist yaklaşımıyla yalnız operation tipi, IDs, hash snapshot, sayfa sayısı/coordinate özeti, delivery outcome ve consent metin sürümü tutulur. Dosya adı gerektiğinde safe display name olarak export manifestte bulunur; event'te zorunlu değildir.

## Silme gerçeği

Uygulama silme sonrası kendi store'undaki bytes'ı kaldırır ve tombstone bırakır. SSD wear leveling, filesystem snapshot, OneDrive/version history veya daha önce alınmış backup kopyalarının fiziksel olarak geri getirilemez silinmesini garanti edemez. UI bu sınırı açıklar.

## Güvenlik release checklist

- Root/path escape ve symlink testleri yeşil.
- Command injection testleri yeşil.
- Token plaintext hiçbir DB/log/event fixture'ında yok.
- Event mutation trigger testleri yeşil.
- Redaction extraction testleri yeşil.
- Container process non-root; servisler localhost bind.
- Dependency/image taraması incelenmiş; kritik açık varsa çözülmüş veya release durdurulmuş.
- Gerçek belge ve `.env` Git history'de yok.

