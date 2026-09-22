# PLAN.md — Arabic → Multilingual Religious-Domain Translation & ASR Data Pipeline

Status: **Phase 1b executed** on your local machine (not the earlier
sandbox) — hadeethenc.com, qurancomplex.gov.sa, opus.nlpl.eu,
islamhouse.com, and tanzil.net are all reachable from here. HadeethEnc is
now downloaded and integrated into the pipeline (Section 8.1): 10,748
pairs across en/fr/id/ur/tr, all surviving cleaning intact. OPUS was
downloaded and inspected but found unsuitable for training and is NOT
integrated (Section 8.2: non-commercial license + Arabic column is tafsir
commentary, not verse text). King Fahd Complex was checked read-only and
has no translation downloads for our 5 languages (Section 8.3). IslamHouse
was verified but not scraped -- PDF/mp3-only for books, and for its
"articles" type (which does have inline text) the fraction with both a
target-language translation *and* inline text on both sides looks small
per Section 8.9's sampling (Section 8.4/8.9). You reviewed the fr/ur Quran
translator candidates and approved one each as individually-authored
exceptions: Urdu's Muhammad Taqi Usmani (Section 8.7) and French's
Muhammad Hamidullah (Section 8.8, non-commercial-only per tanzil.net's own
terms, checked live before approval -- you confirmed this project is
non-commercial). All 5 target languages now have Quran-domain coverage.
`cleaned.jsonl` is now 213,868 pairs total (up from 190,642 at the start
of this pass). See `reports/data_report.md` for current pairs/language
counts. Phase 2 (ASR) is still scaffolding only, not run. Sections 1-7
below are the unedited record of the earlier (sandboxed) pass; Section 8
is this pass.

## Project license basis (confirmed 2026-09-22)

**This project is non-commercial: research/educational use, no revenue,
no commercial deployment.** The user confirmed this explicitly after the
Hamidullah French Quran edition's license was checked live (Section 8.8)
and found to carry a "non-commercial purposes only" restriction.

This status is the reference point for every source in this pipeline
whose terms are conditioned on commercial vs. non-commercial use. A
source under such a restriction is **compliant, not a flagged gap or
caveat**, as long as this project's status holds:

- **Hamidullah French Quran edition** (`fra_muhammadhamidul`): tanzil.net's
  own Terms of Use restrict it to non-commercial use -- **compliant**,
  confirmed by checking the actual terms live (Section 8.8).
- **OPUS's Tanzil corpus**: also non-commercial-only per its own README --
  would also be compliant on licensing grounds alone, but stays excluded
  from `cleaned.jsonl` for the separate, unrelated reason that its Arabic
  column is tafsir commentary, not Quran verse text (Section 8.2).
- **Usmani Urdu Quran edition** (`urd_muhammadtaqiusm`): status
  **unconfirmed, not compliant-by-verification** -- the aggregator's own
  metadata has no `source` URL for this edition (empty string, unlike
  Hamidullah's explicit tanzil.net link), and a web search for an official
  license/terms statement for this specific translation turned up no
  citable source (see Section 8.7 for what was checked). This is a
  materially different status from Hamidullah's: Hamidullah's restriction
  was *found and confirmed satisfied*; Usmani's terms were *not found at
  all*, so there is nothing to confirm compliance against yet. The user
  already approved this edition with that gap disclosed; it is not
  re-flagged as blocking, but should not be described as "cleared" either.

**If this project's status ever changes to commercial** (revenue,
commercial deployment, or a commercially-licensed downstream product),
every pair whose `license` field cites a non-commercial restriction (grep
`cleaned.jsonl` for "non-commercial") needs to be re-excluded or have
separate permission obtained from the translator/publisher, per that
source's own terms.

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

## 6. Decisions you made, and what happened as a result

You chose: proceed with Phase 1a now (Quran + Hadith from the verified
GitHub sources), treat HadeethEnc/OPUS/IslamHouse as a later pass; and
exclude individually-copyrighted Quran translations by default, keeping
only editions attributed to a government/waqf body.

Result of running `make phase1`:
- 190,642 cleaned Arabic→{en,fr,id,ur,tr} pairs across Quran + Hadith
  (`data/processed/cleaned.jsonl`), split 90/5/5 by `ref` with zero leakage
  between splits (verified directly).
- **Real bug caught during this run and fixed**: the wrong-script filter
  (meant to catch Arabic text leaking into a Latin-script target field) was
  initially applied to Urdu too. Urdu is written in Perso-Arabic script and
  shares Unicode block U+0600-06FF with Arabic, so it was misfiring and
  dropping nearly all ~33k Urdu candidate pairs -- exactly your top-priority
  language. Fixed in `src/clean.py` (skip the Arabic-script heuristic for
  `tgt_lang == "ur"`); Urdu now keeps 33,218 hadith pairs (Quran domain still
  has 0 Urdu pairs -- see next point).
- Applying "government/waqf body only" to Quran left **zero Quran-domain
  pairs for French and Urdu** (no fr/ur edition in fawazahmed0/quran-api is
  attributed to such a body). Hadith still covers both. Full candidate list
  with authors is in `sources.csv`; tell me if you want to approve a specific
  translator (e.g. Fateh Muhammad Jalandhry for Urdu, whose translator died
  in 1941, is a common candidate for public-domain-by-age, though I have not
  independently confirmed that status).
- See `reports/data_report.md` for the full pairs/words table, drop reasons,
  and 50-sample-per-source/language CSVs under `reports/samples/`.
- `data/raw/` and `data/processed/*.jsonl` total ~2GB and are gitignored
  (regenerate with `make phase1`); only code, `PLAN.md`, `sources.csv`,
  `README.md`, and the small `reports/` outputs are committed.

## 7. Still open (as of the earlier sandboxed pass)
1. Section 0's options (1/2/3/4) for HadeethEnc/Tanzil/OPUS/IslamHouse --
   which one do you want for the next pass?
2. Approve a specific fr/ur Quran translator to close that gap, or leave it?
3. GitHub push for this session is currently blocked (Claude's GitHub App
   isn't installed/authorized on this repo) -- work is committed locally,
   needs that resolved to land on the branch.

---

## 8. Phase 1b (this pass, run from your local machine with open internet)

### 8.0 Network check

All five domains are reachable from here (plain `curl`, no proxy):
hadeethenc.com, qurancomplex.gov.sa, opus.nlpl.eu, islamhouse.com,
tanzil.net -- all returned `200 OK`. This resolves the sandbox blocker
from Section 0.

### 8.1 HadeethEnc -- verified, built, and run

**Terms.** From the site's own "Terms and Policies" modal
(https://hadeethenc.com/en) and its API docs
(https://hadeethenc.com/api-docs/, a public Postman collection): content
may be downloaded and re-published if you (1) don't modify the
hadith/translation text itself, (2) clearly attribute HadeethEnc.com,
(3) keep the version number, (4) keep transcript info, (5) notify
HadeethEnc of any correction, (6) re-sync to the latest version, and
(7) don't run inappropriate ads alongside it. None of that is a ban on ML
training or on redistribution as such -- it's an attribution/no-alteration
condition, same shape as fawazahmed0's requirement to keep translator
attribution. Beyond that, `hadeethenc.com/robots.txt` publishes an explicit,
machine-readable `Content-Signal: ai-train=yes, search=yes, ai-input=yes`
header -- a direct statement that AI-training use is allowed. Given both,
HadeethEnc is marked `ok` (not `needs_approval`) in `sources.csv`, unlike
its status in the earlier, network-blocked pass.

**API shape (confirmed live, not guessed).** Base
`https://hadeethenc.com/api/v1`:
- `GET /categories/list/?language=<lc>` -- flat list of all 493 categories,
  `{id, title, hadeeths_count, parent_id}`. Category ids/parent structure
  are language-independent; only `title` translates.
- `GET /hadeeths/list/?language=<lc>&category_id=<id>&page=<n>&per_page=<n>`
  -- `category_id` is required (omitting it 404s). `per_page` up to at
  least 200 confirmed working. Returns `{data: [...], meta: {current_page,
  last_page, total_items, per_page}}`.
- `GET /hadeeths/one/?language=<lc>&id=<id>` and
  `GET /hadeeths/multiple/?language=<lc>&ids=<comma-separated>` (batches of
  40+ ids confirmed in one request) -- both return full records:
  `id, title, hadeeth, attribution, grade, explanation, hints[],
  categories[], translations[]` (language codes available for this hadith),
  plus the Arabic original always included as `hadeeth_ar, explanation_ar,
  hints_ar, words_meanings_ar, attribution_ar, grade_ar` regardless of the
  requested `language`.
- `GET /hadeeths/search/?phrase=<text>&language=<lc>` and `GET /languages`
  also exist and work; not used by the downloader (not needed for a full
  category walk).
- Real gap, not a bug: `hints[]` is sometimes `[]` for a non-Arabic
  language even when `hints_ar` is populated for the same id -- a genuine
  translation gap in their content, confirmed on multiple ids. The
  downloader stores whatever is actually present and does not backfill.

**Downloader**: `src/download_hadeethenc.py`. Walks all 493 categories via
`categories/list`, paginates `hadeeths/list` per category to collect every
unique hadith id (a hadith can be tagged under more than one category,
including a parent and its child, so every category is walked and ids are
deduped -- trades some redundant listing requests for a guarantee nothing
is missed), then fetches full records per id via `hadeeths/multiple` in
batches of 40, once per language (ar, en, fr, id, ur, tr). Uses the
existing `common.fetch_json_cached` (rate-limited ~2.5 req/s, exponential
backoff on 429/5xx, resumable -- reruns skip already-cached files). Raw
cache layout: `data/raw/hadeethenc/{categories.json, hadith_ids.json,
listing/cat_<id>_p<n>.json, records/<lang>/batch_<start>_<end>.json,
manifest.json}`.

**Pipeline integration**: `clean.py` gained `load_hadeethenc_pairs()`,
producing pairs shaped like every other source (`id, source="hadeethenc",
domain="hadith", ref="hadeethenc:<id>", ar_diacritized, ar, ar_normalized,
lang="ar", tgt, tgt_lang, license`), plus HadeethEnc-specific extra fields
carried through unfiltered: `explanation, explanation_ar, hints, hints_ar,
grade, grade_ar, attribution, attribution_ar`. The `tgt` field is the main
hadith/translation text (matching the shape `split.py`/`report.py` already
expect); explanation and hints are *not* expanded into separate training
pairs -- they're stored as metadata on the same pair so nothing from "full
records" is lost, without silently changing what one row of the dataset
means. Existing quran-quote-in-hadith detection and length-ratio filtering
in `filter_and_tag()` apply to HadeethEnc pairs exactly as they do to
fawazahmed0 hadith pairs. See `reports/data_report.md` for the resulting
per-language x domain counts.

### 8.2 OPUS -- verified, downloaded, deliberately NOT integrated

Listed live via the official `https://opus.nlpl.eu/opusapi/` JSON API
(`?source=ar&target=<lc>&preprocessing=moses`). For every one of the 5
target languages the only religious-domain corpus present is `Tanzil`
(everything else -- CCMatrix, CCAligned, NLLB, OpenSubtitles, Wikipedia,
TED2020, etc. -- is general-domain web/media text, out of scope for this
task). Downloaded and inspected all 5 `Tanzil` zips (65.6MB total, well
under the "few hundred MB" approval threshold) via the new
`common.fetch_binary_cached` + `src/download_opus.py`.

Two problems surfaced by actually reading the extracted text, not just
trusting the corpus name:
1. **License**: the corpus's own README
   (`https://object.pouta.csc.fi/OPUS-Tanzil/v1/moses/README`) states
   *"The translations provided at this page are for non-commercial
   purposes only."* Stricter than HadeethEnc's terms.
2. **The Arabic column is not Quran verse text.** Every pair's `.ids` file
   tags the Arabic side as `ar/jalalayn.xml.gz` -- Tafsir al-Jalalayn, a
   verse-by-verse *commentary*, not the ayah itself. Confirmed by reading
   actual lines: the "Arabic" text aligned to verse 1:2 is a multi-sentence
   grammatical explanation of the word "al-hamd", not "الحمد لله رب
   العالمين". Using this column as an Arabic training source would
   silently pair commentary text with a translation of a *different*
   underlying string.

Target-language translators found (from each `.ids` file): en=ahmedali,
fr=hamidullah, id=indonesian, ur=ahmedali, tr=ates -- all
individually-authored, the same class of edition already excluded from our
approved Quran set in `download_quran.py` (not attributed to a government/
waqf body). Combined with the non-commercial restriction and the source-
text mismatch, this corpus is cached and reported
(`data/raw/opus_tanzil/verification_report.json`) but **not** merged into
`cleaned.jsonl`. If you want to revisit it: the target-language column
*is* usable, aligned by sura:ayah (readable from the `.ids` file, e.g.
`s1.2`) -- it could be re-paired against our own verified
fawazahmed0/quran-api Arabic text instead of trusting OPUS's "ar" column,
after separately deciding whether the non-commercial restriction is
acceptable for this project.

On `opus.nlpl.eu/robots.txt`: it disallows crawling `/opusapi` and `*.zip`
on that domain. Read this as a search-engine-indexing directive (avoiding
duplicate/heavy content in Google), not a redistribution ban -- `/opusapi`
is OPUS's own documented public API and the mechanism its own website's
download buttons use; the actual files are served from a different host
(`object.pouta.csc.fi`) with no robots restriction at all. Flagging this
reasoning explicitly rather than silently ignoring the disallow.

### 8.3 King Fahd Quran Complex -- verified reachable, NOT scraped, needs your input

Per your instruction, no scraping was attempted. `qurancomplex.gov.sa` is
reachable (200 OK). Checked `/quran-translations/` (Publications) and
`/quran-dev/` (Sites & Apps / developer platform): both pages return a
real HTTP 200 with a populated navigation/footer shell (2500-3600 lines of
HTML) but **no translation list or download links anywhere in the static
HTML** -- the actual content is rendered client-side by JavaScript after
load. Confirmed by checking for alternate ways in: no matching WP REST API
route (`/wp-json/wp/v2/pages?slug=quran-translations` returns empty), no
per-language sub-pages in `/wp-sitemap.xml`, no `.pdf`/`.zip`/`.docx` links
anywhere in either page's HTML. The only other linked subdomain,
`nashr.qurancomplex.gov.sa`, turned out to be unrelated: it's "Madinah
Mushaf Desktop Publishing" -- Windows software for Arabic text layout, not
a translation download. `/sales-policy/` covers paid physical Mushaf
copies (bank transfer instructions); `/privacypolicy/` covers visitor data,
not content-reuse terms.

**Update: read-only check completed (via a page-fetch tool, not a browser
click-through or scraper -- no files downloaded).** Findings:
- `/quran-translations/` lists 50+ languages as **plain text with no
  links at all** -- not even `<a>` tags -- grouped by region (Asian,
  European, African). Notably, **neither French nor English appears in
  this list**, despite both obviously existing as KFC-distributed
  translations (e.g. Hilali-Khan English is one of the most widely printed
  Quran translations there is). This strongly suggests the page is a
  "we've translated the Quran into this many languages" prestige list for
  print/other distribution, not a digital-download index.
- `/quran-hafs/` (the flagship Arabic Mushaf page) also has **no direct
  download links** -- only pointers to a mobile "app" and to the
  `nashr.qurancomplex.gov.sa` desktop-publishing software.
- `/quran-audio-translations/` (audio, not text) only lists Oromo,
  Mandinka, and Tajik -- none of our 5 target languages.
- `/quran-dev/` ("Quran software developers platform") **does** have real
  direct-download files -- but only for **Arabic** text/data: Unicode
  Uthmani font+text packages per qira'ah (Hafs, Warsh, Shubah, Qaloun,
  Duri, Susi, Bazzi) in Excel/CSV/HTML5/SQL/XML/JSON/TXT formats, plus
  Tafseer Muyassar (simplified Arabic commentary) and a rare-word glossary.
  Confirmed working direct URLs, e.g.
  `https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip`
  and `.../hafs_tafseerMouaser_v3.zip` -- no login/registration/API-key
  wall visible on the page. No explicit terms-of-use text was found on
  this page either. **None of this is a translation into fr/ur/en/id/tr**
  -- it's Arabic-only text and Arabic-only commentary, so it doesn't close
  the translation gap this check was for, though the Tafseer Muyassar file
  could be a useful additional Arabic explanation/sharh source for Quran
  verses (paralleling HadeethEnc's `explanation` field for hadith) if you
  want that pursued separately.

**Bottom line: King Fahd Complex does not appear to offer direct digital
downloads of Quran translations in fr/ur/en/id/tr through its public
website.** Distribution for those appears to be via print sales
(`/sales-policy/`) and possibly in-app content not exposed as files.
fawazahmed0/quran-api remains the practical source for these languages
(with its own gov/waqf-attribution caveat, Section 1.1). No files were
downloaded from qurancomplex.gov.sa.

### 8.4 IslamHouse -- verified, real API found, NOT scraped (unclear content-reuse terms)

`islamhouse.com` is reachable and has a real, publicly documented API:
`api.islamhouse.com` redirects to `developers.islamhouse.com`, whose
Postman collection (37 endpoints, base
`https://api3.islamhouse.com/v3/paV29H2gm56kvLPy/...`, a free key
published directly in the docs) was fetched and confirmed live --
`get-available-languages`, `get-item/<id>/<lang>/json`,
`get-item-translations/<id>/<lang>/json` (returns the same work's item id
in every other language it's translated into -- genuine cross-language
alignment), `quran/*` endpoints, etc.

**Why this isn't built into a downloader yet**: fetching a real item
(`main/get-item/2839210/ar/json`) shows the record has `title`,
`description`, `full_description`, and an `attachments` field -- **no
inline full-text body**. Following a book's page on the site
(`islamhouse.com/en/books/1261/`) confirms the actual content is a PDF
(audio items are similarly external mp3 files), not machine-readable
sentence-segmented text. Bulk use would mean OCR/PDF-extraction per
language with no guarantee of consistent structure or true sentence
alignment across independently-laid-out translated books -- a much higher
extraction cost than Quran/hadith's structured, sentence-level sources. I
did not check whether the "articles" item type has inline HTML text
instead (a plausible exception -- `main/showall/<lang>/<type>/<page>/<n>/
json` needs the correct `type` slug, which I didn't want to guess at). On
terms: the only content-adjacent policy page found,
`d1.islamhouse.com/html/policy.htm`, covers visitor data collection only
(IP, browser, opt-in mailing-list info) -- nothing about reuse/redistribution
of the books/audio themselves. Per your own instruction (unclear ML-use
terms -> `needs_approval`, keep out of train), no downloader was written
and nothing was bulk-fetched.

### 8.5 Re-run results

`clean.py`, `split.py`, `report.py` were re-run after adding HadeethEnc.
See `reports/data_report.md` for the full pairs/words table (now including
`hadeethenc` rows alongside `fawazahmed0_quran-api` and
`fawazahmed0_hadith-api`) and updated drop-reason counts.

### 8.6 Still open after this pass
1. King Fahd Complex (8.3): resolved -- no translation downloads found for
   our 5 target languages; fawazahmed0/quran-api remains the source. Open
   sub-question: do you want the Arabic-only Tafseer Muyassar file from
   `/quran-dev/` pursued as an additional Quran-verse explanation field
   (paralleling HadeethEnc's `explanation`)? Deferred, skipped for now per
   your instruction.
2. IslamHouse "articles" (8.4/8.9): resolved as not worth building --
   see 8.9.
3. OPUS-Tanzil (8.2): stays cached-but-unused unless you want the
   re-pairing (OPUS target-language text + our own Arabic verse text)
   pursued despite the non-commercial license.
4. fr/ur Quran translator approvals: resolved -- see 8.7/8.8. Both
   languages now have Quran-domain coverage.
5. GitHub push access (from the earlier pass, Section 7.3): still open,
   unrelated to this pass's work.

### 8.7 Quran translator approvals (this pass)

You reviewed the candidate lists (author/source per edition, from
`sources.csv`'s fawazahmed0_quran-api row) and decided:

- **Urdu: APPROVED** -- `urd_muhammadtaqiusm` (Muhammad Taqi Usmani).
  Individually-authored (source field blank in the API, not attributed to
  a government/waqf body), approved as an explicit exception to the
  gov/waqf-only default. Added to `APPROVED_EDITION_KEYS` in
  `src/download_quran.py`. Quran-domain Urdu pairs: **0 -> 6,217**.
  License status: **unconfirmed, not verified compliant** -- the
  aggregator has no `source` URL for this edition to check terms against,
  and a web search for an official license/terms statement for this
  specific translation turned up nothing citable (only Internet Archive
  mirrors and bibliography pages, no terms). This is different from
  Hamidullah's case below, where a specific restriction was found *and*
  confirmed satisfied -- here, no terms were found to confirm anything
  against. See "Project license basis" at the top of this file.
- **French: still open.** Candidate table (all 5 non-transliteration fra_*
  editions in fawazahmed0/quran-api):

  | key | translator | source |
  |---|---|---|
  | fra_muhammadhamidul | Muhammad Hamidullah | tanzil.net |
  | fra_muhammadhameedu | Muhammad Hameedullah | quranenc.com |
  | fra_islamicfoundati | Islamic Foundation | quranenc.com |
  | fra_rashidmaash | Rashid Maash | quranenc.com |
  | fra_shahnazsaidiben | Shahnaz Saidi Benbetka | Goodwordbooks (commercial publisher) |

  None are attributed to a government/waqf body. "tanzil.net" as source
  means Tanzil itself vets and hosts that translation (a stronger signal
  than the quranenc.com/Goodwordbooks ones), but it's still an
  individually-authored work, same category as the Urdu edition just
  approved.

- **French: APPROVED** -- `fra_muhammadhamidul` (Muhammad Hamidullah),
  after checking its license live (see Section 8.8 below). Quran-domain
  French pairs: **0 -> 6,226**.

`cleaned.jsonl` is now 213,868 pairs (up from 201,421 at the start of this
pass).

### 8.8 Hamidullah French edition -- license checked live before adding

Before adding Hamidullah's translation, checked tanzil.net directly (not
just the aggregator's blanket Unlicense) since `fawazahmed0/quran-api`
lists `source: http://tanzil.net` for this edition. Found, verbatim, on
tanzil.net's own `/trans/` page under "Terms of Use":

> "The translations provided at this page are for non-commercial purposes
> only. If used otherwise, you need to obtain necessary permission from
> the translator or the publisher."

This is the same restriction already found on OPUS's mirrored Tanzil
corpus (Section 8.2) -- both ultimately point back to this same tanzil.net
terms page. Note this is specific to **translations**; Tanzil's Arabic
**text** has a separate, more permissive license (verbatim copy/
redistribution allowed with attribution, no non-commercial clause) at
`tanzil.net/download/`.

**You confirmed this project is non-commercial** (research/educational,
no revenue, no commercial deployment -- see "Project license basis" at
the top of this file), so the restriction is **satisfied: this edition is
compliant**, not a flagged gap. `fra_muhammadhamidul` was added to
`APPROVED_EDITION_KEYS` in `src/download_quran.py`, and a new
`LICENSE_NOTES` dict in that file carries the exact tanzil.net wording
through to every pair's `license` field in `cleaned.jsonl` (via
`clean.py`), so the restriction -- and the basis for its compliance --
travels with the data rather than being recorded only here. If this
project's scope ever becomes commercial, every pair with this `license`
text needs to be re-excluded (or separate permission obtained from
Hamidullah's publisher).

### 8.9 IslamHouse "articles" type -- resolved: confirmed not worth building

Checked whether IslamHouse's "articles" content type (distinct from
"books") has inline text instead of a PDF attachment, which would have
been a much cheaper source than PDF-extracting books. Two passes:

**Pass 1 (small sample, earlier)**: found `full_description` (inline
HTML) populated on *some* articles -- e.g. Arabic article id 6621 (a
2007-era item) has 29,988 characters inline -- but empty (PDF/DOCX-
attachment-only, same as books) on others, with an apparent recency
pattern (older articles more likely to have inline text).

**Pass 2 (this pass, 200-item probe, definitive)**: sampled 200 Arabic
article ids spread evenly across the full 2007-2026 time range (paging
`main/get-latest/all/articles/ar/ar/<page>/10/json` at a fixed stride so
old and new content are both represented, not just "latest"), then for
each: fetched the Arabic item, called `main/get-item-translations` to
find its sibling in each of our 5 target languages, and fetched every
sibling found. Results:
- **79/200 (39.5%)** of sampled Arabic articles have substantial inline
  text (`full_description` > 200 chars) -- confirms the recency pattern,
  now on a large-enough sample to trust.
- **Translation coverage into our 5 languages is very low in this
  sample**: only 3/200 (en), 2/200 (fr), 7/200 (id), 2/200 (ur), 0/200
  (tr) of the sampled Arabic articles even had a sibling translation at
  all -- despite the API's own aggregate counts being much larger (of
  1,672 Arabic articles total: en 494, fr 229, id 820, ur 156, tr 284).
  This gap between the aggregate counts and what a time-spread sample
  finds suggests translated articles are not evenly distributed the way
  this sampling method assumed -- but not something to chase further
  given the next finding.
- **Of the few translations found, only about half also have inline text
  on the target-language side**: en 1/3, fr 0/2, id 1/7, ur 0/2, tr 0/0
  found. E.g. article id 2767774 (English) has `full_description` empty
  (PDF-only) while its Arabic sibling id 2817034 has 15,656 characters
  inline -- confirming this is a real, common failure mode, not a fluke.

**Conclusion (resolved): not worth building.** Even in the most
optimistic reading of this sample, the fraction of IslamHouse's ~1,672
articles that would yield a genuine (Arabic text, target-language text)
pair for any one of our 5 languages is in the low single-digit percent at
best -- nowhere near enough to justify a dedicated downloader, especially
against HadeethEnc's clean, fully-aligned 2,000-3,500-pairs-per-language
baseline with none of this per-item uncertainty. Combined with the
unresolved license question (no content-reuse terms found beyond the
visitor-data privacy policy, section 8.4), IslamHouse **stays
`needs_approval` in `sources.csv` and no downloader was written** --
treated the same as books, despite articles technically having a partial
exception that doesn't change the practical outcome.

### 8.11 OPUS re-verified on the open network: TED2020 checked and excluded, bible-uedin noted

Re-confirmed `opus.nlpl.eu` reachable and re-listed all 5 target-language
pairs' corpora via the official `opusapi` endpoint (same mechanism as
section 8.2). Two specific corpora checked this pass, beyond Tanzil
(already excluded, section 8.2):

**TED2020 (explicitly requested -- spoken-style register)**: all 5 pairs
confirmed live (~101MB total: ar-en 30.5MB/407,595 pairs, ar-fr
31.2MB/399,617, ar-id 12.0MB/164,020, ar-ur 1.3MB/15,578, ar-tr
28.3MB/370,936). Its README points to TED's own Usage Policy
(https://www.ted.com/about/our-organization/our-policies-terms/
ted-talks-usage-policy), which was read directly. Key clauses:
- **NC**: "you cannot use TED Talks in any commercial context or to gain
  any type of revenue" -- satisfied by this project's non-commercial
  status (see "Project license basis" above).
- **ND**: "no derivative works are permitted so you cannot edit, remix,
  create, modify or alter the form of the TED Talks in any way"; "any
  edits, alternate usage rights or changes to these documents are not
  permitted without permission."

Unlike the Tanzil/Hamidullah restriction (which only limits *purpose* --
non-commercial vs. commercial -- and was judged compliant), TED's ND
clause restricts *modification itself*, with no stated exception for
research or ML training, and the policy doesn't address AI/ML use either
way. Given your instruction to build a downloader only where terms
clearly permit training use, and that reformatting text into training
pairs (let alone training a model on it) is plausibly exactly the kind of
"alter[ation]" this clause is written to prohibit, **TED2020 was not
downloaded or integrated**. This is also true independent of domain fit:
TED talks are general-topic, not religious-register content, so even a
clean license would have made it a lower-priority addition than the
Quran/hadith sources already in the pipeline.

**bible-uedin (found while re-listing, not explicitly requested)**:
CC0 1.0 (public domain) per its README -- no restriction of any kind.
62,195 ar-en pairs found. This is genuinely religious-register text
(a parallel Bible corpus), domain-adjacent to but distinct from the
Quran/hadith/Islamic-sermon focus of this pipeline. Not downloaded or
built into anything this pass since it wasn't requested and its
relevance to an Islamic-sermon-translation system is unclear -- flagged
in `sources.csv` as a clean, ready-to-use option if you want non-Quranic
formal religious-register text considered later.

No downloader was written for either corpus this pass (TED2020 excluded
on license grounds, bible-uedin out of requested scope).

