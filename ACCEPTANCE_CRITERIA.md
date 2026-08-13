# ACCEPTANCE_CRITERIA

Öncelik: P0 olmadan release yok; P1 release adayı için beklenir fakat gerekçeli known limitation olabilir; P2 sonraki iterasyondur. Kanıt sütununa test adı, screenshot değil mümkünse otomatik test/komut ve exit code yazılır.

## Kurulum ve yerellik

- [ ] **P0** Temiz repoda `.env.example` mevcut, gerçek `.env` Git'e dahil değil.
- [ ] **P0** Docker Desktop açıkken `docker compose up --build` tek komutuyla web, API, worker ve DB hazır olur.
- [ ] **P0** `localhost:3000` açılır; `/health` 200, `/ready` bütün zorunlu dependency'ler hazırsa 200 döner.
- [ ] **P0** Merge/split gibi core işlemlerde ağ bağlantısı kapalıyken vendor çağrısı yapılmaz ve işlem başarılıdır.
- [ ] **P0** Servisler public interface'e varsayılan bind edilmez.
- [ ] **P1** Stop/start sonrası belge metadata ve dosyaları korunur.

## Veri bütünlüğü

- [ ] **P0** Upload sonrası original SHA-256, disk byte'larından yeniden hesaplanan hash ile aynıdır.
- [ ] **P0** Hiçbir operation original path'ini yazma modunda açmaz; original mtime/hash değişmez.
- [ ] **P0** Her başarılı operation yeni version number, relative path, SHA-256 ve event üretir.
- [ ] **P0** Başarısız/cancelled operation final output yayımlamaz ve önceki sürümleri değiştirmez.
- [ ] **P0** Output atomik publish öncesi pikepdf ile açılır ve beklenen invariant doğrulanır.
- [ ] **P0** Event satırları API ve doğrudan uygulama DB rolü ile update/delete edilemez.

## Dosya alma, preview ve uyarılar

- [ ] **P0** Oversize, sahte uzantı, bozuk PDF ve path traversal filename güvenli hata verir.
- [ ] **P0** Unicode/güvenli display name korunurken disk path'i kullanıcı girdisiyle oluşturulmaz.
- [ ] **P0** PDF sayfa preview'ları doğru sıra ve sayıda üretilir; loading ve recoverable error görünür.
- [ ] **P0** Encryption işlemi engeller veya desteklenen açık aksiyonu söyler.
- [ ] **P0** Form/signature/font riskleri dönüşümden önce görünür warning'dir.

## PDF operasyonları

- [ ] **P0 Merge** En az iki PDF seçilebilir, sıra korunur, page count toplamdır.
- [ ] **P0 Split** Range parser doğru sayfaları üretir; invalid/out-of-bounds range reddedilir; multi-output ZIP manifest hash'leri eşleşir.
- [ ] **P0 Reorder** Permutation tüm sayfaları tam bir kez gerektirir; çıktı sırası UI ile aynıdır.
- [ ] **P0 Rotate** Yalnız seçilen sayfalar 90/180/270 döner; output valid PDF'tir.
- [ ] **P0 Compress** Üç profil çalışır; önce/sonra boyut raporu doğrudur; daha büyük sonuç saklanırsa uyarılır.
- [ ] **P0 Watermark** Text, opacity, rotation, position ve page scope nihai çıktıda doğrulanır.
- [ ] **P0 Redact** İşaretlenen metin content extraction sonucunda yoktur; yalnız overlay yapılmış çıktı kabul edilmez.
- [ ] **P0 OCR** Tarama fixture'ı aranabilir metin katmanı kazanır; dil unavailable hatası recoverable'dır.
- [ ] **P0 Office** DOCX/XLSX/PPTX geçerli PDF üretir; LibreOffice unavailable/timeout açık hata verir.

## Signature-lite

- [ ] **P0** UI her aşamada bunun nitelikli/düzenlemeye tabi e-imza olmadığını belirtir.
- [ ] **P0** Alanlar sayfa sınırları içinde yerleşir; server coordinate doğrulaması vardır.
- [ ] **P0** Consent olmadan seal yapılamaz; consent metin sürümü, zaman ve belge hash'i kaydedilir.
- [ ] **P0** Token DB/log/event içinde plaintext saklanmaz, expiry ve single-use kontrolü vardır.
- [ ] **P0** Final PDF hash'i seal event ve receipt ile aynıdır.
- [ ] **P0** SMTP yokken ana akış manual delivery ile kullanılabilir; unavailable API uygulamayı çökertmez.
- [ ] **P0** Government identity/qualified certificate/legally binding garantisi yoktur.

## Yaşam döngüsü ve taşınabilirlik

- [ ] **P0** Download doğru byte, güvenli filename ve no-sniff header döndürür.
- [ ] **P0** Expiry sonrası yeni operation/download policy gereği engellenir; event oluşur.
- [ ] **P0** Delete onay ister, byte'ları siler, event/tombstone'u korur ve tekrar çağrıda idempotent davranır.
- [ ] **P0** Export ZIP original, sürümler, manifest ve audit JSONL içerir; hash'ler doğrulanır.
- [ ] **P0** Backup PostgreSQL dump + store + hash manifest içerir.
- [ ] **P0** Restore yalnız boş hedefe yapılır, path/hash mismatch'te abort eder ve round-trip testini geçer.

## UX ve hata yönetimi

- [ ] **P0** Her ana akışta empty/loading/progress/success/recoverable error/blocked state tanımlıdır.
- [ ] **P0** Hata gövdesi stable code, safe message, recoverable ve correlation id taşır.
- [ ] **P0** Double submit idempotency key ile tek operation üretir.
- [ ] **P0** Disk full, DB unavailable ve tool unavailable durumları veri kaybetmez.
- [ ] **P1** Keyboard-only reorder ve alan yerleşimi için kullanılabilir alternatif vardır.
- [ ] **P1** Otomatik accessibility taramasında kritik ihlal yoktur.

## Test ve teslim

- [ ] **P0** Core transformation focused unit/integration testleri geçer.
- [ ] **P0** Playwright upload→preview→merge→download→audit/export happy path geçer.
- [ ] **P0** Backend lint/type/test, frontend lint/type/test ve `git diff --check` başarılıdır.
- [ ] **P0** README gerçek setup, architecture, permissions, data location, backup/restore ve exclusions içerir.
- [ ] **P0** `COMMANDS.md` exact commands, platform, tarih ve exit code'larla doldurulmuştur.
- [ ] **P0** Her büyük slice anlamlı commit ile kapanmış; remote varsa push edilmiş, yoksa blokaj kaydedilmiştir.
- [ ] **P0** Git history'de secret, gerçek kullanıcı belgesi veya generated local data yoktur.

## Kesin red koşulları

Aşağıdakilerden biri varsa release reddedilir: original hash değişimi; event update/delete mümkün olması; vendor'a belge yüklenmesi; secret commit'i; redaction'ın yalnız görsel overlay olması; consent olmadan sealing; restore'un dolu hedefi ezmesi; tek komut first run'ın temiz ortamda çalışmaması; P0 E2E'nin başarısız olması.

