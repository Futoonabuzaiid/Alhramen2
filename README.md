# Arabic → Multilingual Religious-Domain Translation & ASR Data Pipeline

Training data pipeline for Arabic → {English, French, Indonesian, Urdu,
Turkish} machine translation and (Phase 2) Arabic ASR, for a real-time
sermon-translation system.

Read **`PLAN.md`** first -- it documents what was verified against live
sources vs. what's still blocked, and the decisions this Phase 1 build
was made under (source approval policy, network constraints).

## Status

Phase 1 (Quran + Hadith translation pairs) is built and run. HadeethEnc,
Tanzil (used only for license wording, text itself is covered via
`fawazahmed0/quran-api`), OPUS, and IslamHouse are **not yet included** --
they were unreachable from this development sandbox's network and need to
be verified from an unrestricted network before any downloader is written
for them. See `sources.csv` for exact status per source.

Phase 2 (ASR) is scaffolding only -- `src/audio_prep.py`, `src/transcribe.py`,
`src/review_tool.py` exist but have not been run and require separate
approval plus GPU/audio dependencies.

## Project structure

```
PLAN.md              source verification findings + decisions
sources.csv           name, url, method, license, languages, status, notes
data/raw/             cached raw API responses, one subfolder per source, never modified
data/processed/       cleaned.jsonl, dropped.jsonl, train/valid/test.jsonl (+ per-language-pair files)
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
 "ref": "quran:2:255 or hadith:bukhari:1", "ar_diacritized": "...",
 "ar": "...", "ar_normalized": "...", "lang": "ar",
 "tgt": "...", "tgt_lang": "en|fr|id|ur|tr", "license": "...",
 "quran_quote_refs": ["quran:..."]  // only present when detected}
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

make download-phase1   # or: make download-quran / make download-hadith
make clean              # writes data/processed/cleaned.jsonl + dropped.jsonl
make split               # writes data/processed/{train,valid,test}*.jsonl
make report               # writes reports/data_report.md + reports/samples/*.csv

# or all at once:
make phase1
```

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

- Quran: only editions attributed to a government/waqf body (King Fahd
  Complex, Indonesian Ministry of Religious Affairs, Turkey's Diyanet) are
  included in `cleaned.jsonl`, per an explicit decision to exclude
  individually-copyrighted translations by default. This currently leaves
  **no Quran-domain pairs for French or Urdu** -- see
  `reports/data_report.md` "Known gaps".
- Hadith: all available translations are included, each pair's `license`
  field records the named translator so this can be revisited; see
  `sources.csv` and `PLAN.md` for the reasoning.
- Everything sourced from `fawazahmed0/quran-api` and `fawazahmed0/hadith-api`
  (Unlicense / public domain for the aggregator's compilation).
