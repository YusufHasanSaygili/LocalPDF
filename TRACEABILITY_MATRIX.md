# TRACEABILITY_MATRIX

| Gereksinim | Slice | Ana task | Kabul/test kanıtı |
|---|---|---|---|
| Tek komut first run | S00/S12 | S00-T08, S12-T02 | Clean Compose smoke |
| Immutable originals | S01/S02 | S01-T04, S02-T01 | hash/mtime integration |
| Versioned outputs | S01+ | S01-T01/T05 | version uniqueness + reopen |
| Append-only event | S01 | S01-T03 | mutation trigger test |
| Merge/split | S03 | S03-T01/T02 | page/hash/ZIP tests |
| Reorder/rotate | S04 | S04-T01 | permutation/rotation tests |
| Compress/watermark | S05 | S05-T01/T02 | size/snapshot/reopen |
| Permanent redact | S06 | S06-T02/T04 | extracted text absent |
| OCR | S07 | S07-T01/T02 | searchable output/offline |
| Office-to-PDF | S08 | S08-T02 | DOCX/XLSX/PPTX integration |
| Previews/warnings | S02 | S02-T02/T03 | page count/feature fixtures |
| Signature-lite | S09 | S09-T01–T06 | consent/token/hash/delivery |
| Expiry/download/delete | S10 | S10-T01–T03 | fake clock/race/header |
| Export/backup/restore | S10/S12 | S10-T03–T05 | round-trip + manifest |
| Validation/safe filename | S02/S11 | S02-T01, S11-T01/T02 | malicious corpus |
| Graceful unavailable API/tool | S07–S11 | S11-T03 | fault injection matrix |
| UI states | S02–S11 | feature tasks | component/state matrix |
| Focused tests + 1 E2E | S03–S12 | S12-T01/T05 | test suites + Playwright |
| README/env/exact commands | S00/S12 | S00-T07, S12-T04/T06 | docs review + execution record |
| Git slice commits/push | Her slice | son task | log/remote/push record |
| Exclusions | S00/S09/S12 | content docs/tests | forbidden-copy/scope review |

