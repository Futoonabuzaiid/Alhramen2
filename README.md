# Arabic → Multilingual Religious-Domain Translation & ASR Data Pipeline

Training data pipeline for Arabic → {English, French, Indonesian, Urdu,
Turkish} machine translation and (Phase 2) Arabic ASR, for a real-time
sermon-translation system.

Read **`PLAN.md`** first -- it documents what was verified against live
sources vs. what's still blocked, and the decisions this Phase 1 build
was made under (source approval policy, network constraints).

## Status

Phase 1 (Quran + Hadith translation pairs, now including HadeethEnc's
hadith text + sharh/hints) is built and run. Tanzil is used only for
license wording (its text is covered via `fawazahmed0/quran-api`). OPUS's
Tanzil corpus was downloaded and inspected but is **deliberately excluded**
from the training pipeline (its Arabic column is Tafsir al-Jalalayn
commentary, not Quran verse text, and its license is non-commercial-only
-- see PLAN.md section 8.2). King Fahd Complex and IslamHouse were
verified reachable but **not scraped** -- KFC's translation pages are
JavaScript-rendered with no static content to check terms against, and
IslamHouse's book/audio content is PDF/mp3-only with no confirmed
content-reuse license. See `sources.csv` and `PLAN.md` section 8 for exact
status per source.

Phase 2 (ASR) is scaffolding only -- `src/audio_prep.py`, `src/transcribe.py`,
`src/review_tool.py` exist but have not been run and require separate
approval plus GPU/audio dependencies.

IslamHouse's "articles" content type (which does have inline text, unlike
books) and OPUS's TED2020/bible-uedin corpora were also investigated and
found not worth building into the pipeline -- see PLAN.md sections
8.9-8.11.

`src/prepare_for_training.py` (NLLB-tokenizer-based length rule, ~128
tokens/side) is built -- see "Training prep" below.

## Project structure

```
PLAN.md              source verification findings + decisions
sources.csv           name, url, method, license, languages, status, notes
data/raw/             cached raw API responses, one subfolder per source, never modified
data/processed/       cleaned.jsonl, dropped.jsonl, train/valid/test.jsonl (+ per-language-pair files), train_ready.jsonl
data/processed/gold_test/  empty, for manually-added real sermon sentences (never used in training)
data/raw/haramain_khutab/  empty, for manually-added sermon audio/text (not scraped)
src/                  pipeline scripts
logs/                 one log file per script run
reports/              data_report.md + reports/samples/*.csv
```

## Schema

One JSON object per line in every `data/processed/*.jsonl` file:

```json
{"id": "...", "source": "...", "domain": "quran|hadith|sharh|khutba|general",
 "ref": "quran:2:255 or hadith:bukhari:1 or hadeethenc:10842", "ar_diacritized": "...",
 "ar": "...", "ar_normalized": "...", "lang": "ar",
 "tgt": "...", "tgt_lang": "en|fr|id|ur|tr", "license": "...",
 "quran_quote_refs": ["quran:..."],  // only present when detected
 "explanation": "...", "explanation_ar": "...",  // hadeethenc only, when present
 "hints": ["..."], "hints_ar": ["..."],           // hadeethenc only, when present
 "grade": "...", "grade_ar": "...",               // hadeethenc only, when present
 "attribution": "...", "attribution_ar": "..."}    // hadeethenc only, when present
```

- `ar_diacritized`: original Arabic text, untouched.
- `ar`: diacritics/tatweel stripped, alef variants (أ إ آ → ا) unified.
- `ar_normalized`: `ar` with the additional ى→ي normalization applied (kept
  separate since it's a lossier transform some downstream uses won't want).
- `ref` is stable across all 5 target languages of the same verse/hadith --
  used for splitting and dedup.

## Re-running each phase

```bash
pip install -r requirements.txt

# On a machine where `python3` isn't on PATH (e.g. Windows with the `py`
# launcher), override the interpreter: make PYTHON=py <target>

make download-phase1   # download-quran + download-hadith + download-hadeethenc + download-opus
make clean              # writes data/processed/cleaned.jsonl + dropped.jsonl
make split               # writes data/processed/{train,valid,test}*.jsonl
make report               # writes reports/data_report.md + reports/samples/*.csv

# or all at once:
make phase1
```

`download-opus` caches and inspects OPUS's Tanzil corpus but does **not**
feed it into `clean.py` -- see `src/download_opus.py`'s docstring and
PLAN.md section 8.2.

Every download step is resumable: it caches raw JSON under `data/raw/` and
skips re-fetching files already on disk. Delete a specific cached file to
force a re-fetch of just that one. Requests are throttled to ~2.5 req/s with
exponential backoff on retryable errors (see `src/common.py`).

`make clean` and `make split` are deterministic given the same
`data/raw/` contents (fixed seed in `src/split.py`), so they're safe to
re-run after editing the filtering/normalization logic.

Phase 2 targets (`make phase2-*`) are defined in the `Makefile` but are not
part of `make all` -- run them individually, only after reviewing PLAN.md's
Phase 2 section and installing the extra dependencies listed (commented out)
in `requirements.txt`.

## License policy applied in this build

- Quran: editions attributed to a government/waqf body (King Fahd Complex,
  Indonesian Ministry of Religious Affairs, Turkey's Diyanet) are included
  by default, plus explicit user-approved exceptions: Urdu's Muhammad Taqi
  Usmani translation, and French's Muhammad Hamidullah translation
  (both individually-authored; approved after reviewing the full candidate
  list -- see PLAN.md sections 8.7-8.8). **Hamidullah's edition carries a
  non-commercial-only restriction** (tanzil.net's own Terms of Use,
  checked live before approval) -- the exact restriction text is carried
  in every one of its pairs' `license` field. All 5 target languages now
  have Quran-domain coverage.
- Hadith: all available translations are included, each pair's `license`
  field records the named translator so this can be revisited; see
  `sources.csv` and `PLAN.md` for the reasoning.
- Everything sourced from `fawazahmed0/quran-api` and `fawazahmed0/hadith-api`
  (Unlicense / public domain for the aggregator's compilation).
- HadeethEnc: attribution-required (not a ban on ML training or
  redistribution as such), and its `robots.txt` explicitly publishes
  `Content-Signal: ai-train=yes` -- included in `cleaned.jsonl`. Every pair
  carries `license`/`attribution` fields so the required credit isn't lost
  downstream. See PLAN.md section 8.1.
- OPUS's Tanzil corpus is downloaded (`make download-opus`) but **not**
  included in `cleaned.jsonl` -- its Arabic column is tafsir commentary,
  not Quran verse text, and its license is non-commercial-only. See
  PLAN.md section 8.2.

## Training prep

```bash
make prepare-for-training   # writes data/processed/train_ready.jsonl
                              # (downloads only the NLLB tokenizer, a few MB)
```

`prepare_for_training.py` reads `data/processed/train.jsonl` (never
`cleaned.jsonl` itself, which stays the canonical untruncated record) and
applies a length rule targeting ~128 NLLB tokens/side: pairs already
within budget are kept as-is; pairs that can be cleanly split into an
equal number of sentences on both sides (each within budget) are split
into multiple rows sharing the original `ref`; everything else is
truncated to 128 tokens. Every output row is tagged `"prep":
"as_is"|"split"|"truncated"`. See `reports/data_report.md`'s hadith
word-count percentile table and the script's own log for exact counts.
