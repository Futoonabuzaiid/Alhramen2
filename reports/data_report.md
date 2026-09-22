# Data Report

Generated from 213868 kept pairs, 18770 dropped pairs.

## Pairs by source x domain x target language

| source | domain | tgt_lang | pairs | avg ar words | avg tgt words |
|---|---|---|---:|---:|---:|
| fawazahmed0_hadith-api | hadith | en | 35689 | 71.4 | 78.6 |
| fawazahmed0_hadith-api | hadith | fr | 31610 | 68.2 | 81.8 |
| fawazahmed0_hadith-api | hadith | id | 30739 | 73.8 | 107.0 |
| fawazahmed0_hadith-api | hadith | tr | 29012 | 72.7 | 83.0 |
| fawazahmed0_hadith-api | hadith | ur | 33224 | 72.1 | 118.7 |
| fawazahmed0_quran-api | quran | en | 5849 | 13.3 | 31.8 |
| fawazahmed0_quran-api | quran | fr | 6226 | 12.8 | 24.4 |
| fawazahmed0_quran-api | quran | id | 12469 | 12.8 | 24.1 |
| fawazahmed0_quran-api | quran | tr | 12085 | 13.1 | 18.0 |
| fawazahmed0_quran-api | quran | ur | 6217 | 12.8 | 35.4 |
| hadeethenc | hadith | en | 2328 | 55.5 | 101.4 |
| hadeethenc | hadith | fr | 1790 | 57.6 | 111.4 |
| hadeethenc | hadith | id | 2260 | 53.3 | 74.2 |
| hadeethenc | hadith | tr | 2150 | 54.1 | 72.7 |
| hadeethenc | hadith | ur | 2220 | 53.2 | 108.0 |

## Hadith Arabic word-count percentiles

Word counts (whitespace-split, not tokenizer counts) on the `ar` field, one row per (hadith, target-language) pair -- so a hadith with 5 translations is counted 5 times, weighting by how often that length appears in training data.

| source | n | p50 | p90 | p99 | max |
|---|---:|---:|---:|---:|---:|
| fawazahmed0_hadith-api | 160274 | 57 | 120 | 270 | 1921 |
| hadeethenc | 10748 | 38 | 98 | 311 | 1817 |
| **all hadith** | 171022 | 56 | 119 | 273 | 1921 |

See `src/prepare_for_training.py` for the actual NLLB-tokenizer-based length rule (targets ~128 tokens, not words) applied on top of this data; its own report covers how many pairs were split/truncated/left as-is.

## Dropped items by reason

| reason | count |
|---|---:|
| empty_side | 16093 |
| length_ratio_outlier | 2666 |
| identical_source_target | 9 |
| wrong_script_target | 2 |

Full list with source/target snippets: `data/processed/dropped.jsonl` (18770 rows).

## Known gaps

- **Quran domain has no approved French edition.** No fr Quran edition in fawazahmed0/quran-api is attributed to a government/waqf body, so the Quran domain currently contributes 0 pairs for fr. (Urdu's gap is closed: you approved Muhammad Taqi Usmani's individually-authored translation -- see PLAN.md section 8.7.) Hadith still covers fr. See `sources.csv` (fawazahmed0_quran-api row) for the full French candidate list if you want to approve one.
- **sharh/hints fields**: now included for the `hadeethenc` source (`explanation`, `hints`, `grade`, `attribution` and their `_ar` counterparts, stored as extra fields on each pair, not expanded into separate rows). See PLAN.md section 8.1.
- **OPUS (Tanzil corpus) was downloaded and inspected but deliberately excluded**: its Arabic column is Tafsir al-Jalalayn commentary, not Quran verse text, and its license is non-commercial-only. See PLAN.md section 8.2.
- **King Fahd Complex has no direct translation downloads for fr/ur/en/id/tr** (checked read-only, nothing downloaded): its /quran-translations/ page lists 50+ languages as plain text with no links at all, and doesn't even list French or English. Its /quran-dev/ developer platform has real download links, but only for Arabic text/commentary, not translations. fawazahmed0/quran-api remains the source for these languages. See PLAN.md section 8.3.
- **IslamHouse was verified but not scraped** -- it has a real public API, but book content is PDF-only (no inline text). Its 'articles' type does have inline text on some items (39.5% of a 200-item sample), but a full probe found the yield of usable (Arabic + target-language, both with inline text) pairs is negligible -- at best a handful per language. No content-reuse license was found beyond a visitor-privacy policy either way. See PLAN.md sections 8.4 and 8.9.
- **OPUS's TED2020 corpus was checked and not built**: its Usage Policy is No-Derivatives ('you cannot edit, remix, create, modify or alter the form... in any way'), with no research/ML carve-out -- judged not clearly compatible with training use. bible-uedin (CC0, fully unrestricted) was also found but is out of this pipeline's requested scope (Bible text, not Islamic). See PLAN.md section 8.11.
- **37.4% of training pairs get truncated at the ~128-token length rule** (`src/prepare_for_training.py`): 120,044 as-is, 208 split, 71,811 truncated, out of 192,063 input pairs. Truncation is lossy (cuts mid-sentence); the low split rate (0.1%) means most over-length pairs don't have a clean 1:1 sentence-count match between Arabic and the target language. See the hadith word-count percentiles above -- p99 is 270+ words, and some outliers reach ~1,900 words (full isnad chains), which is what drives this.