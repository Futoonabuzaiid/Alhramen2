# Data Report

Generated from 190642 kept pairs, 18776 dropped pairs.

## Pairs by source x domain x target language

| source | domain | tgt_lang | pairs | avg ar words | avg tgt words |
|---|---|---|---:|---:|---:|
| fawazahmed0_hadith-api | hadith | en | 35717 | 71.4 | 78.5 |
| fawazahmed0_hadith-api | hadith | fr | 31608 | 68.3 | 81.8 |
| fawazahmed0_hadith-api | hadith | id | 30739 | 73.8 | 107.0 |
| fawazahmed0_hadith-api | hadith | tr | 29002 | 72.7 | 82.9 |
| fawazahmed0_hadith-api | hadith | ur | 33218 | 72.1 | 118.7 |
| fawazahmed0_quran-api | quran | en | 5812 | 13.3 | 31.8 |
| fawazahmed0_quran-api | quran | id | 12469 | 12.8 | 24.1 |
| fawazahmed0_quran-api | quran | tr | 12077 | 13.1 | 18.0 |

## Dropped items by reason

| reason | count |
|---|---:|
| empty_side | 16093 |
| length_ratio_outlier | 2681 |
| wrong_script_target | 2 |

Full list with source/target snippets: `data/processed/dropped.jsonl` (18776 rows).

## Known gaps

- **Quran domain has no approved French or Urdu edition.** Per your instruction to exclude individually-authored translations by default, no fr/ur Quran edition in fawazahmed0/quran-api is attributed to a government/waqf body, so the Quran domain currently contributes 0 pairs for fr and ur. Hadith still covers both languages. See `sources.csv` (fawazahmed0_quran-api row) for the full candidate list if you want to approve a specific translator.
- **No sharh/hints fields yet** -- these come only from HadeethEnc, which is blocked from this sandbox's network. See PLAN.md section 2.
- **OPUS, IslamHouse general-domain text not yet included** -- same network blocker.