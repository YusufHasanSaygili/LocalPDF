# UX_STATES

## Ürün dili ve ortak kurallar

- Kısa, eylem odaklı, suçlamayan mesajlar.
- Teknik hata ayrıntısı varsayılan gizli; correlation id “Ayrıntılar” içinde.
- Silme, redaction ve signature seal geri döndürülemez etkiyi açıklar.
- Her sayfada görünür ama rahatsız etmeyen uyarı: “Düşük riskli kişisel kullanım içindir. Nitelikli elektronik imza veya kimlik doğrulama sağlamaz.”
- Renk tek sinyal değildir; icon + başlık + metin kullanılır.

## Ortak state bileşenleri

| State | Görünüm | Eylem |
|---|---|---|
| Empty | Ne olmadığı + ilk adım | “Dosya seç” |
| Loading | Skeleton; kısa işte spinner | Gereksiz cancel yok |
| Queued | Kuyrukta konum/durum | Güvenliyse iptal |
| Running | Gerçek progress veya indeterminate | Refresh sonrası sürer |
| Success | Sonuç, hash, boyut, version | İndir / başka işlem / audit |
| Recoverable error | Ne oldu, veri güvende mi | Retry veya düzeltme |
| Blocked | Neden devam edilemez | Unlocked copy gibi net aksiyon |
| Partial | Preview gibi türetilmiş veri eksik | Belgeyle devam + preview retry |

## Kütüphane

- Empty: yerel veri konumu kısa açıklama, upload CTA.
- Upload loading: filename, byte progress, cancel.
- Scan loading: “Dosya doğrulanıyor”; tarayıcı kapanırsa job durumu sonra bulunur.
- Duplicate: mevcut original hash/tarih ve yeniden kullan/yeni belge kaydı seçimi.
- Success: original badge, immutable açıklaması, SHA-256 kopyala.
- Expired/deleted: işlem CTA'ları disabled; policy ve event linki.

## Operation editor

- Input seçilmeden CTA disabled ve nedeni görünür.
- Warning banner tipleri: `may_change_fonts`, `may_flatten_forms`, `invalidates_signature`, `encrypted_blocked`.
- İşlem öncesi summary: kaynak hash/versiyon, parametre, tahmini çıktı sayısı.
- Double click'te tek job; button anında submitting state.
- Success kartı: version, output hash, page count, byte difference, download ve audit.
- Recoverable: aynı idempotency key semantiğini koruyan “Tekrar dene”.

## Araçlara özel durumlar

### Merge/split

- Merge minimum iki dosya; reorder için mouse ve keyboard buttons.
- Split range inline parse preview: “3 PDF oluşacak: 1–3, 5, 8–10”.
- Çoklu output success ZIP + tek tek download sunar.

### Compress

- Profilin neyi değiştirebileceği açıklanır.
- Output büyükse sarı bilgi: “Bu belge zaten optimize edilmiş olabilir.”

### Redact

- Seçimler sayfa listesinde sayıyla gösterilir.
- Confirmation: redaksiyon yeni output'ta kalıcıdır; original korunur.
- Success: “Metin katmanı otomatik kontrol edildi; görüntü içeriğini ayrıca gözle kontrol edin.”

### OCR

- Kurulu diller capability'den gelir; unavailable option seçilemez.
- Uzun job progress sayfa bazlı; tahmini süre garanti edilmez.

### Office

- Dönüşümden önce font/layout warning.
- LibreOffice unavailable ise ilgili araç disabled; PDF araçları aktif kalır.

### Signature-lite

- Her ekranda scope warning.
- Invite: SMTP ready ise “E-posta ile gönder”; değilse “Bağlantıyı kopyala”.
- Consent sayfası document hash, signer label, consent text ve checkbox gösterir.
- Seal sonrası hash receipt indirilebilir; “hukuki geçerlilik garantisi” dili kullanılmaz.

## Silme, expiry ve backup

- Delete modal belge adı, original+sürümler byte etkisi ve backup kopyalarının etkilenmeyeceğini belirtir.
- Kullanıcı belge adını yazmak zorunda değildir; iki net adımlı confirmation yeterli.
- Backup state: hazırlanıyor, doğrulanıyor, başarı (path/manifest), hata (disk/permission).
- Restore UI yoktur; güvenlik için documented local command'a yönlendirilir.

## Accessibility kabulü

- Visible focus ve mantıklı tab sırası.
- Drag işlemlerinin button/keyboard alternatifi.
- Progress `aria-live=polite`; kritik error `role=alert`.
- Thumbnail alt text sayfa numarası/rotation içerir.
- Canvas alanları liste görünümünde coordinate/sayfa olarak düzenlenebilir.
- Modal focus trap ve kapatma sonrası focus iadesi.

## Mesaj örnekleri

- `PDF_ENCRYPTED`: “Bu PDF parola ile korunuyor. Kilidi kaldırılmış bir kopya yükleyin. Orijinal dosyanız değiştirilmedi.”
- `TOOL_UNAVAILABLE`: “Office dönüşümü şu anda hazır değil. PDF araçlarını kullanmaya devam edebilirsiniz.”
- `STORAGE_FULL`: “Çıktı kaydedilemedi; diskte yeterli alan yok. Önceki dosyalarınız korundu.”
- `OUTPUT_VALIDATION_FAILED`: “Üretilen PDF doğrulanamadı ve yayınlanmadı. Orijinaliniz güvende.”

