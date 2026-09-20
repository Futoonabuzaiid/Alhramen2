# PLAN.md — Arabic → Multilingual Religious-Domain Translation & ASR Data Pipeline

Status: **DRAFT — awaiting your approval before any code is written or bulk data is downloaded.**

## 0. Important constraint discovered during verification

This session runs in a sandboxed environment whose outbound network access is
restricted by an egress proxy to GitHub domains only
(`github.com`, `raw.githubusercontent.com`). I attempted to open or curl every
source in the task, and the proxy returned `403` (policy denial, not a site
error) for:

- `hadeethenc.com`
- `tanzil.net`
- `opus.nlpl.eu`
- `www.islamhouse.com`
- `huggingface.co`
- `cdn.jsdelivr.net`
- `api.github.com` / `codeload.github.com` (only `raw.githubusercontent.com` works)

I could **not** open their docs pages, test a single API request, or confirm
current license text for any of them. I did not guess and silently proceed —
each is marked `needs_verification` in `sources.csv` with exactly what's
unconfirmed. Two of the five original translation sources (fawazahmed0's
`quran-api` and `hadith-api` on GitHub) *were* fully reachable and I verified
them live end-to-end (details below).

**This changes what I can deliver today.** Options, so you can pick before I go further:

1. You approve running the downloads for the GitHub-reachable sources now
   (Quran + Hadith parallel text, Phase 1 items 2+3 combined — see below),
   while HadeethEnc/OPUS/IslamHouse stay blocked until verified elsewhere.
2. You run the (small, read-only) verification curl commands yourself on a
   machine with normal internet and paste me the results, and I incorporate
   them before writing the downloaders for those sources.
3. This environment's network policy gets widened to allow those domains for
   this session, and I re-run verification myself.
4. Any combination — e.g., proceed with what's verified now, and treat
   HadeethEnc/OPUS/IslamHouse as a second pass.

I'd suggest **option 1 for a quick first deliverable + option 2 or 3 for the
rest**, since HadeethEnc and Tanzil-quality hadith/Quran text are your biggest
domain-relevant sources. But it's your call — tell me which and I'll adjust
this plan before touching any pipeline code.

---

## 1. What I verified live (works today)

### 1.1 `fawazahmed0/quran-api` (GitHub) — **VERIFIED, use this**
- Fetched `editions.json` (raw.githubusercontent.com/fawazahmed0/quran-api/1/editions.json): 492 editions.
- Fetched and diffed `ara-quransimple.json` (plain Arabic) and
  `ara-quranuthmanihaf.json` (diacritized Arabic): both **6236/6236 verses**,
  keyed by `{chapter, verse}` — matches the Quran's known verse count, so this
  can serve as `ar_diacritized` (uthmanihaf) and the basis for our own
  normalized `ar` (we do our own diacritic/tatweel/alef normalization in
  `clean.py`, we do not trust their "no-diacritics" variant for that).
- Fetched `eng-ahmedali.json`: 6236 verses, same `{chapter, verse}` keys →
  confirms alignment works by `(chapter, verse)` across every edition, so
  `ref` = `quran:{chapter}:{verse}`.
- Target-language non-transliteration editions available (with translator
  name in each edition's `author` field): **en 52, fr 5, id 6, ur 11, tr 29**.
- License: repo `LICENSE` file = Unlicense (public domain), fetched and read.
- **Caveat (real, not hypothetical)**: the Unlicense covers fawazahmed0's
  compilation, not necessarily each underlying translation's original
  copyright. Some editions are well-known copyrighted works (e.g. Abdel
  Haleem/Oxford University Press, Saheeh International). I've flagged this in
  `sources.csv` and propose: prefer editions whose `source` field names a
  government/waqf body (King Fahd Complex, Indonesian Ministry of Religious
  Affairs, etc. — these are the same texts Tanzil itself distributes), and
  mark the rest `needs_approval` rather than silently including them.
- **This replaces Tanzil.net as the practical Quran source** since tanzil.net
  itself is blocked from here. If you need Tanzil's exact wording/attribution
  for compliance reasons, that still needs a live check from an unrestricted
  network — the text itself is the same Tanzil-derived corpus.

### 1.2 `fawazahmed0/hadith-api` (GitHub) — **VERIFIED, use this**
- Fetched `editions.json`: structure is `{book: {name, collection: [editions]}}`,
  10 books (bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah, malik,
  nawawi, qudsi, dehlawi).
- Fetched `ara-bukhari.json` and `eng-bukhari.json`: **both 7589 hadiths**,
  same order, linked by `hadithnumber` (and `arabicnumber`) — confirmed by
  direct diff, not assumption.
- Coverage across all 5 target languages exists for: bukhari, muslim,
  abudawud, tirmidhi, nasai, ibnmajah, malik. nawawi/qudsi/dehlawi are missing
  some languages (e.g. no ur/tr/id for qudsi/dehlawi) — I will use what
  exists and record gaps, not fabricate translations.
- License: repo `LICENSE` = Unlicense. Same aggregator-vs-original-copyright
  caveat as above applies to translator attributions.
- This gives us **hadith text** directly; it does **not** give us the
  *sharh* (explanation) or *hints* fields the task wants from HadeethEnc —
  those are HadeethEnc-specific and stay blocked pending verification.

## 2. What is blocked and unverified (do not build code against these yet)

| Source | What's blocked | What I'd need before writing a downloader |
|---|---|---|
| HadeethEnc | Entire domain, incl. `/api/v1/...` | Confirm actual API base path, auth (if any), pagination, and whether ToS allows ML training/redistribution. Confirm how sharh/hints are linked to hadith id. |
| Tanzil.net | Entire domain | Only needed now for exact license wording/attribution per translation, since fawazahmed0/quran-api substitutes for the text itself. |
| OPUS | Entire domain | Confirm current corpus list for ar-en/ar-fr/ar-id/ar-ur/ar-tr, exact download URL pattern (`opus.nlpl.eu/download.php?f=...`), and per-corpus license (varies — some OPUS corpora are CC-BY, some are more restrictive; must check the specific corpus page, not assume). |
| IslamHouse | Entire domain, incl. `/en/api/` | Confirm whether a public API exists at all (my attempt found nothing reachable). Confirm ToS explicitly allows extraction for ML use — if unclear, this stays `needs_approval` per your own instructions. |
| Common Voice / MASC / SADA (HF) | `huggingface.co` | Phase 2 only. Need to read each dataset card for size/license/gating before even reporting on them properly, per your instruction not to download without approval anyway. |

## 3. Proposed schema mapping (for the verified sources)

```
Quran pair:
  id: "quran:{chapter}:{verse}:{tgt_lang}"
  source: "fawazahmed0_quran-api"
  domain: "quran"
  ref: "quran:{chapter}:{verse}"
  ar_diacritized: from ara-quranuthmanihaf.json
  ar: derived in clean.py (strip diacritics/tatweel, normalize alef/ya) from ar_diacritized
  lang: "ar"
  tgt: from {lang}-{translator}.json at same (chapter, verse)
  tgt_lang: en|fr|id|ur|tr
  license: "Unlicense (aggregator) — verify original translator copyright; see sources.csv"

Hadith pair:
  id: "hadith:{book}:{hadithnumber}:{tgt_lang}"
  source: "fawazahmed0_hadith-api"
  domain: "hadith"
  ref: "hadith:{book}:{hadithnumber}"
  ar_diacritized: from ara-{book}.json .text
  ar: derived in clean.py
  lang: "ar"
  tgt: from {lang}-{book}.json .text at same hadithnumber
  tgt_lang: en|fr|id|ur|tr
  license: "Unlicense (aggregator) — verify original translator copyright; see sources.csv"
```

No `sharh`/hints field is populated yet — that depends entirely on HadeethEnc,
which is blocked.

## 4. Revised phase order (given the constraint)

**Phase 1a (ready now, pending your go-ahead on option 1 above):**
1. `src/download_quran.py` — pull `editions.json`, then every needed edition
   JSON from `raw.githubusercontent.com/fawazahmed0/quran-api/1/...`, cache
   raw responses under `data/raw/fawazahmed0_quran/`, rate-limited (this is
   GitHub raw content, still politeness-limited to 2-3 req/s and resumable).
2. `src/download_hadith.py` — same pattern for hadith-api, cached under
   `data/raw/fawazahmed0_hadith/`.
3. `src/clean.py` — normalization, footnote/marker stripping, quran-quote
   detection inside hadith text (match against the Tanzil/quran-api Arabic
   index), length-ratio filtering, dedup.
4. `src/split.py` — split by `ref`, 90/5/5, fixed seed, all translations of
   one hadith/verse in the same split.
5. `data/processed/gold_test/` scaffold + README (empty, for your manual
   sermon sentences).
6. `reports/data_report.md` + per-source/language CSV samples.

**Phase 1b (blocked until a source is verified via one of the options above):**
- HadeethEnc extraction (text + sharh + hints).
- OPUS ar-{en,fr,id,ur,tr} download (TED2020 + Tanzil-derived corpora).
- IslamHouse (only if ToS confirmed to allow it; otherwise stays `needs_approval` permanently and is excluded from training).

**Phase 1c (manual, no scraping):**
- `data/raw/haramain_khutab/README.md` describing the expected aligned
  Arabic/translation format for you to add sermons manually.

**Phase 2 (scaffolding only, per your instructions — no downloads without separate approval):**
- `src/audio_prep.py`, `src/transcribe.py`, `src/review_tool.py` as specified.
- A short written report on Common Voice Arabic / MASC / SADA once
  huggingface.co is reachable (or you relay their license/size/gating info).

## 5. Politeness / engineering defaults (apply once approved)
- Rate limit 2-3 req/s with jittered exponential backoff on 429/5xx.
- Every raw HTTP response cached verbatim under `data/raw/<source>/` before
  any processing touches it; scripts check cache before re-fetching (resumable).
- `data/raw/` is never modified after write; all transforms write to
  `data/processed/`.
- Logs per phase under `logs/`.
- One `Makefile` target per phase (`make download-quran`, `make download-hadith`,
  `make clean`, `make split`, `make report`), so any phase can be re-run
  independently.

## 6. Questions for you before I proceed
1. Which option from Section 0 do you want (1/2/3/4)?
2. For quran-api editions with clear individual copyright (Abdel Haleem, Saheeh
   International, etc.) — exclude by default, or include with a
   `needs_approval` license tag and let you decide per-translation later?
3. OK to proceed with Quran + Hadith (Phase 1a) now while HadeethEnc/OPUS/IslamHouse
   verification happens separately, so you have a working pipeline sooner?
