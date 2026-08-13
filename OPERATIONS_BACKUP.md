# OPERATIONS_BACKUP

## Varsayılan yerel veri konumu

Compose host path'i `.env` içindeki `LOCAL_DATA_DIR` ile belirlenir. Windows örneği `./data` kullanır; böylece repo klasörü taşınabilir. PostgreSQL için `POSTGRES_DATA_DIR` verilmezse named volume kullanılabilir, fakat kolay export/backup için uygulama backup script'i tek otoritedir.

Kullanıcıya UI “Ayarlar > Veri” ekranında resolved container/store bilgisi değil, host tarafından yapılandırılmış veri dizini ve backup hedefi gösterilir.

## Normal çalışma

```powershell
docker compose up --build
```

Arka planda çalıştırmak:

```powershell
docker compose up -d --build
docker compose ps
```

Güvenli durdurma:

```powershell
docker compose down
```

`down -v` normal dokümantasyonda kullanılmaz; DB volume'unu silebilir.

## Backup içeriği

Her backup arşivi:

- `database.dump` (`pg_dump --format=custom`)
- `store/` altında originals, outputs ve gerekli preview/export metadata'sı
- `manifest.json` (schema version, created_at UTC, app version, DB dump hash)
- `files.jsonl` (relative path, byte size, SHA-256)
- `README_RESTORE.txt` (sürüm ve restore komutu)

Secret `.env` varsayılan olarak backup'a girmez. Kullanıcı `.env` dosyasını ayrı güvenli yerde saklamalıdır.

## Tutarlı backup algoritması

1. Hedef dizini doğrula; repo root veya data root'un kendisi olamaz.
2. Maintenance lock ile yeni mutating operation'ları kısa süreli durdur.
3. Running job'ların bitmesini bekle veya açıkça abort et; zorla yarım çıktı alma.
4. PostgreSQL custom dump üret.
5. Store'daki DB-referenced dosyaları manifest sırasıyla arşive ekle.
6. Her dosyanın hash/size değerini yaz.
7. Arşivi temp adla oluştur, doğrula, atomik final ada taşı.
8. `backup.completed` event'ini arşiv path'ini değil backup id/manifest hash'iyle yaz.
9. Maintenance lock'u her durumda bırak.

Hedef script sözleşmesi:

```powershell
.\scripts\backup.ps1 -Destination "D:\LocalPDF-Backups"
```

## Restore güvenlik kuralları

- Restore yalnız uygulama durmuşken ve **boş hedef veri dizinine** yapılır.
- Mevcut data/DB üzerine in-place overwrite yoktur.
- Arşiv path traversal, absolute path ve symlink entry içeremez.
- Önce manifest/schema/app compatibility, sonra bütün file hash'leri doğrulanır.
- DB yeni volume'a restore edilir; migration compatibility check yapılır.
- Reconciliation store ile DB'yi karşılaştırır; mismatch varsa restore hazır ilan edilmez.
- Başarıdan sonra kullanıcı yeni dizini `.env` ile seçer ve stack'i açar.

Hedef script sözleşmesi:

```powershell
.\scripts\restore.ps1 -Archive "D:\LocalPDF-Backups\localpdf-2026....tar.zst" -Destination ".\data-restored"
```

## Restore runbook

1. `docker compose down`.
2. Backup arşivinin ayrıca bir kopyasını al.
3. Yeni ve boş restore hedefi oluştur.
4. Restore script'ini çalıştır; exit code 0 ve manifest summary bekle.
5. `.env` içinde restore data/DB hedefini seç.
6. `docker compose up -d`.
7. `/ready`, document count, rastgele original/output hash ve audit event sırasını doğrula.
8. Eski data'yı hemen silme; kullanıcı onayına kadar salt okunur sakla.

## Export ile backup farkı

- Document export: seçili belgeyi başka araca taşıma; original/versions/audit içerir.
- Backup: uygulamanın tamamını felaket kurtarma için alır; DB ve bütün store içerir.
- Download: tek bir dosya baytını alır; audit/manifest içermez.

## Expiry ve deletion

- Expiry bir policy state'tir; grace period environment ile belirlenir.
- Cleanup her geçişte event yazar ve active job/input referansını kontrol eder.
- Explicit delete, store bytes'ını kaldırır ama event log/tombstone kalır.
- Daha önce alınmış backup, işletim sistemi snapshot'ı veya OneDrive geçmişi otomatik silinmez; UI bunu söyler.

## Periyodik doğrulama

- Aylık: backup oluştur ve `--verify-only` çalıştır.
- Her release: geçici boş hedefe tam restore round-trip.
- Disk doluluk uyarısı: temp + beklenen output için güvenlik payı.
- Orphan cleanup: yalnız DB referansı olmayan, grace period'dan eski temp dosyaları; originals/outputs otomatik “tahminle” silinmez.

