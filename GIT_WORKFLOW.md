# GIT_WORKFLOW

## Amaç

GitHub aktivitesini görünür tutarken geçmişi anlamlı, incelenebilir ve bisect edilebilir yapmak. Aktivite uğruna boş commit, yapay dosya oynatma veya test edilmemiş büyük yığın yoktur.

## Branch düzeni

- Varsayılan: `main` korunan/stabil.
- Slice branch'i: `feat/s00-foundation`, `feat/s03-merge-split`, `fix/s11-resilience`.
- Tek geliştirici de olsa doğrudan main yerine slice branch'i tercih edilir.
- Remote/PR zorunlu değil; erişim yoksa yerel commit korunur ve raporlanır.

## Commit kuralları

Conventional Commits:

- `chore: bootstrap localpdf stack`
- `feat(storage): add immutable original store`
- `feat(pdf): add merge and split jobs`
- `test(e2e): cover merge and audited export`
- `docs: document backup and restore`

Bir commit:

- Tek bir mantıksal değişiklik taşır.
- Derlenebilir/test edilebilir ara durum bırakır.
- Secret, `.env`, gerçek PDF, `data/`, backup veya generated output içermez.
- Gerekirse task ID'lerini body'de (`Refs: S03-T01`) taşır.

## Her büyük slice sonunda zorunlu akış

```powershell
git status --short
git diff --check
# Slice'a ait backend/frontend focused test + lint/typecheck komutları
git diff --stat
git add <yalnız-slice-dosyaları>
git diff --cached --check
git diff --cached --stat
git commit -m "feat(scope): meaningful outcome"
git push -u origin <mevcut-branch>
```

Notlar:

- `git add .` körlemesine kullanılmaz; en azından `git status` ve diff gözden geçirilir.
- User'a ait/unrelated değişiklikler stage edilmez, geri alınmaz.
- Push öncesi remote ve branch `git remote -v`, `git branch --show-current` ile doğrulanır.
- Force push, history rewrite, `reset --hard` ve başkasının değişikliğini silme yoktur.
- Push permission/network hatası test başarısızlığı değildir; exact hata raporlanır ve kullanıcıdan yetki istenir.

## Önerilen slice/commit haritası

| Slice | En az anlamlı commit |
|---|---|
| S00 | bootstrap stack + docs/env |
| S01 | schema/event immutability; storage/job engine |
| S02 | upload/library; previews/warnings |
| S03 | merge; split/export UI |
| S04 | reorder/rotate editor |
| S05 | compression; watermark |
| S06 | permanent redaction |
| S07 | local OCR |
| S08 | Office conversion |
| S09 | signature request; consent/seal/delivery |
| S10 | lifecycle; backup/restore |
| S11 | validation/fault UX/a11y |
| S12 | E2E; release docs |

Bu tablo minimum contribution görünürlüğü sağlar; fakat bir commit gereksiz büyüyorsa daha küçük, her biri yeşil commit'lere bölünür.

## PR/teslim açıklaması şablonu

```markdown
## Outcome
<Kullanıcının artık yapabildiği şey>

## Tasks
- Sxx-Tyy

## Validation
- `<exact command>` — exit 0

## Data/security
- Original immutability etkisi
- Event/output hash etkisi
- Yeni env/permission varsa açıklama

## Known limitations
- ...
```

## Final teslim kanıtı

- Branch adı ve HEAD commit SHA
- `git status --short` çıktısı (temiz veya açıklanmış user changes)
- Çalıştırılan test/lint/E2E komutları ve exit code
- Push edilen remote/branch veya açık push blokajı
- Known limitations ve P1/P2 listesi

