# PROJECT_SPEC — LocalPDF

## 1. Amaç

ILovePDF Premium benzeri temel kişisel PDF işlevlerini, dosyaları üçüncü taraf bir sağlayıcıya yüklemeden, tek kullanıcılı ve local-first bir uygulamada sunmak. Kullanıcı orijinal dosyasını her zaman koruyabilmeli, üretilen her çıktının kaynağını ve hash'ini görebilmeli, verisini kolayca yedekleyip dışa aktarabilmelidir.

## 2. Başarı ölçütleri

- Temiz yerel kurulum `docker compose up --build` ile ayağa kalkar.
- Yüklenen orijinal baytlar hiçbir operasyonda değiştirilmez.
- Her başarılı operasyon ayrı bir sürümlü çıktı ve SHA-256 hash üretir.
- Merge, split, reorder, rotate, compress, watermark, redact, OCR ve Office-to-PDF yerelde çalışır.
- PDF sayfaları küçük önizlemelerle gösterilir; olası font/form/imza/şifreleme değişiklikleri işlem öncesinde uyarılır.
- Signature-lite alan yerleşimi, davet, açık rıza kaydı, teslim sonucu ve final PDF hash mühürleme sağlar.
- Event log append-only'dir; zaman, aktör, doküman/çıktı hash'i ve teslim sonucunu taşır.
- Dosyalar indirilebilir, süre sonuna alınabilir, açıkça silinebilir ve yedeklenip geri yüklenebilir.
- Kritik dönüşüm testleri ve en az bir tarayıcı tabanlı E2E happy path geçer.
- Hiçbir hesap, faturalama, telemetri, analytics veya hosted control plane yoktur.

## 3. Kullanıcı ve çalışma varsayımları

- Tek yerel kullanıcı; kimlik doğrulama yoktur.
- Uygulama güvenilen kişisel cihazda veya yerel ağdan dışarı açılmadan çalışır.
- Varsayılan bind adresleri localhost'tur.
- PostgreSQL uygulamanın metadata ve event kayıtlarını tutar; belge baytları kullanıcıya ait yerel dosya deposunda bulunur.
- İnternet bağlantısı temel PDF işlemleri için gerekmez.

## 4. Temel ürün döngüsü

1. Kullanıcı dosya seçer veya sürükleyip bırakır.
2. API dosya adını normalize eder, MIME/magic byte ve boyut doğrular, akış sırasında SHA-256 hesaplar.
3. Orijinal immutable store'a atomik olarak yazılır ve kayıt oluşturulur.
4. Kullanıcı sayfa önizlemelerini ve risk uyarılarını görür.
5. Bir işlem seçer ve parametrelerini doğrular.
6. Job PostgreSQL kuyruğuna yazılır; worker izole geçici dizinde çalışır.
7. Başarıda çıktı yeni sürüm olarak atomik taşınır, hash'lenir, event yazılır ve indirme sunulur.
8. Hata durumunda orijinal ve önceki sürümler korunur; kullanıcı tekrar deneyebilir veya ayrıntıyı açabilir.

## 5. Fonksiyonel gereksinimler

### 5.1 Dosya alma ve kütüphane

- PDF, DOCX, XLSX ve PPTX kabul edilir; Office dosyaları yalnız Office-to-PDF akışında kullanılabilir.
- Uzantıya güvenilmez; magic byte/MIME kontrolü yapılır.
- Dosya adı ekranda korunabilir fakat disk yolu için UUID ve güvenli türetilmiş ad kullanılır.
- Path traversal, NUL, kontrol karakteri, ayrılmış Windows adları ve aşırı uzun adlar reddedilir/normalize edilir.
- Yinelenen hash tespit edilir; kullanıcıya mevcut orijinali yeniden kullanma seçeneği verilir.
- Liste görünümü kaynak, oluşturulma zamanı, sayfa sayısı, boyut, son sürüm ve expiry durumunu gösterir.

### 5.2 Merge

- En az iki PDF seçilir; sürükle-bırak ile dosya sırası belirlenir.
- Şifreli veya bozuk PDF açık ve geri kazanılabilir hata verir.
- Bookmark/form/signature olası kaybı uyarılır.
- Çıktı tek PDF ve yeni version kaydıdır.

### 5.3 Split

- Sayfa aralıkları (`1-3,5,8-10`), tek tek sayfalar veya her N sayfada bölme desteklenir.
- Aralık parser'ı örtüşme, ters aralık ve sayfa sınırı doğrular.
- Birden çok çıktı ZIP olarak indirilebilir; her PDF ayrı version/output kaydıdır ve ortak operation id taşır.

### 5.4 Reorder ve rotate

- Thumbnail grid üzerinde sayfa sırası değiştirilebilir.
- Seçili sayfalar 90/180/270 derece saat yönünde döndürülebilir.
- Orijinal sayfa sayısı ve içerik değişmeden yeni PDF üretilir.

### 5.5 Compress

- `lossless`, `balanced`, `smallest` profilleri sunulur.
- Sonuç orijinalden büyükse bu açıkça belirtilir; kullanıcıya orijinali indirme bağlantısı korunur.
- Form, font, transparency ve dijital imza değişim riski işlem öncesi gösterilir.
- Rapor, önceki/sonraki boyut ve yüzde farkını içerir.

### 5.6 Watermark

- Metin filigranı; metin, font boyutu, renk, opacity, rotation, konum ve sayfa kapsamı ayarlanır.
- Önizleme düşük çözünürlüklü taslaktır; nihai çıktı PDF koordinatlarında deterministik üretilir.
- Boş metin, görünmez opacity ve sayfa dışı yerleşim doğrulanır.

### 5.7 Redact

- Kullanıcı sayfa önizlemesinde dikdörtgen bölgeler çizer.
- Nihai redaksiyon yalnız üstüne siyah kutu çizmek değildir: işaretli alandaki içerik kaldırılır/kalıcı uygulanır ve çıktı yeniden açılarak doğrulanır.
- UI, OCR/metin kalıntısına karşı redaksiyon sonrası doğrulama uyarısı gösterir.
- Gizli metadata'nın ayrıca temizlenip temizlenmeyeceği seçenek olarak sunulur ve event'e yazılır.

### 5.8 OCR

- Tarama PDF'leri için dil seçimi, sayfa kapsamı ve deskew seçeneği vardır.
- Tesseract tamamen yerel çalışır; ağ yoksa özellik çalışmaya devam eder.
- Çıktı aranabilir metin katmanı olan yeni PDF'dir.
- İstenen dil paketi kurulu değilse desteklenen diller listesiyle geri kazanılabilir hata verilir.

### 5.9 Office-to-PDF

- DOCX, XLSX ve PPTX LibreOffice headless ile izole geçici dizinde PDF'e çevrilir.
- Timeout ve process exit code yakalanır.
- Font substitution, layout, forms ve makro işlenmeme riski önceden gösterilir.
- Kaynak Office orijinali immutable store'da kalır; dönüşmüş PDF ilk çıktı sürümüdür.

### 5.10 Önizlemeler ve risk tespiti

- PDF sayfaları WebP/PNG thumbnail olarak asenkron üretilir.
- Büyük belgelerde progressive preview vardır; ilk sayfalar hazır olduğunda UI açılır.
- Encryption, AcroForm, embedded fonts/font eksikliği, signature dictionary ve bozuk xref mümkün olduğu ölçüde tespit edilir.
- Uyarılar engelleyici (`blocked`) veya bilgilendirici (`warning`) sınıfındadır.

### 5.11 Signature-lite

- Belge üzerine text/date/initial/signature placeholder alanı yerleştirilir.
- Signer için ad ve teslim adresi kaydedilebilir; davet sadece yapılandırılmış yerel SMTP varsa gönderilir.
- SMTP yoksa davet bağlantısı kopyalanabilir ve özellik graceful biçimde “manuel teslim” durumuna geçer.
- Signer, belge hash'ini ve rıza metnini görür; checkbox + zaman + rıza metni sürümü kaydedilir.
- Tamamlamada alan görünümü PDF'e düzleştirilir, final SHA-256 hesaplanır ve seal event'i yazılır.
- Teslim sonucu `sent`, `delivered`, `failed`, `manual` olarak event log'a eklenir.
- Bu akış nitelikli elektronik imza, sertifika tabanlı imza veya kimlik doğrulama değildir.

### 5.12 Yaşam döngüsü

- Kullanıcı çıktı/orijinal için expiry tarihi ayarlayabilir veya expiry'yi kaldırabilir.
- Scheduled cleanup worker süresi dolanları önce `expired` durumuna alır; policy'ye göre fiziksel silme uygular.
- Açık silme iki aşamalıdır: onay + delete job. Event ve tombstone kalır, dosya baytları silinir.
- Download akışları güvenli `Content-Disposition` ve no-sniff başlıkları kullanır.
- Backup; DB dump, dosya deposu ve manifest/hash listesini tek arşive alır. Restore ayrı komutla doğrulamalı yapılır.
- Export; seçilen belgenin orijinali, sürümleri ve audit JSON/JSONL dosyasını taşınabilir ZIP olarak üretir.

## 6. Kalite ve güvenlik gereksinimleri

- Varsayılan maksimum yükleme boyutu ve sayfa limiti environment ile ayarlanır.
- API parametreleri Pydantic ile, UI formları TypeScript şemalarıyla doğrulanır.
- Komut satırı çağrılarında shell string birleştirme yoktur; argüman listesi ve timeout kullanılır.
- Worker her job için yeni geçici dizin kullanır ve sonunda temizler.
- Çıktı önce temporary dosyaya yazılır, yeniden açılarak doğrulanır, hash hesaplanır, sonra atomik rename yapılır.
- Log'larda belge içeriği, rıza link token'ı veya secret bulunmaz.
- Hatalar stabil machine-readable kod, kullanıcı dostu mesaj ve correlation id taşır.

## 7. UI durumları

Her ana ekran ve operasyon için empty, loading, progress, success, recoverable error ve unrecoverable/blocked durumları tasarlanır. Uzun işlemler yeniden yüklemeden sonra job id ile izlenebilir. İptal edilebilir aşamalarda Cancel, güvenli tekrar yapılabilen aşamalarda Retry bulunur.

## 8. Kapsam dışı

- Nitelikli veya düzenlemeye tabi elektronik imza
- Devlet kimliği ya da biyometrik kimlik doğrulama
- Tam Acrobat düzeyi metin/görsel düzenleme
- Kurumsal DLP, retention governance, e-discovery veya RBAC
- Hesaplar, ekipler, billing, telemetry, analytics
- Hosted control plane veya vendor'a dosya yükleme
- Mobil native uygulama ve public internet deployment

Detaylar `EXCLUSIONS.md` içindedir.

## 9. Teslim tanımı

Ürün ancak tüm P0 kriterleri geçtiğinde, dokümantasyon gerçek komutlarla doğrulandığında, bir temiz kurulum denemesi yapıldığında, E2E happy path geçtiğinde ve `COMMANDS.md` içindeki final kayıt gerçek çalıştırılan komutlarla doldurulduğunda tamamlanmış sayılır.

