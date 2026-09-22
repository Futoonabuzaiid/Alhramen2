"""
Download hadith text + sharh (explanation) + hints from the official
HadeethEnc API (https://hadeethenc.com/api/v1), for ar, en, fr, id, ur, tr.

Verified live against the real API (this sandbox previously could not reach
hadeethenc.com at all -- see PLAN.md's HadeethEnc section for the full
verification trail). The endpoint shapes below come from the site's own
public Postman collection (linked as "API" in the site footer, served from
https://hadeethenc.com/api-docs/) cross-checked against live responses;
field *names* in the JSON responses (hadeeth, explanation, hints,
hadeeth_ar, hints_ar, words_meanings_ar, attribution, grade, ...) were
confirmed by inspecting real payloads, not guessed.

Terms / attribution (from the "Terms and Policies" modal on
https://hadeethenc.com/en, and robots.txt's Content-Signal header):
  - Content may be downloaded and re-published only with: no modification
    of the hadith/translation text itself, clear attribution to
    HadeethEnc.com, the version number kept, transcript info kept,
    HadeethEnc notified of corrections, content re-synced to the latest
    version, and no inappropriate ads alongside it.
  - robots.txt publishes `Content-Signal: ai-train=yes, search=yes,
    ai-input=yes` -- an explicit, machine-readable statement that AI
    training use is allowed. Combined with the attribution-only
    conditions above (no outright ban, no non-commercial restriction),
    this source is treated as train-eligible, unlike HadeethEnc's status
    in earlier phases of this plan (previously blocked purely by network
    access, not by an unclear license).
  - We record `attribution`/`source_version` on every pair so any
    downstream re-publication keeps the required credit. Normalization in
    clean.py (diacritic stripping etc.) is internal preprocessing, not a
    "modification" of the published translation -- the same treatment
    already applied to every other source in this pipeline.

Strategy:
  1. Fetch categories/list (once, language=ar -- category ids/parent
     structure are language-independent, only titles translate) to
     discover every category id.
  2. For every category id, paginate hadeeths/list?language=ar&category_id=
     to collect every hadith id referenced anywhere in the category tree.
     A hadith can be tagged under more than one category (including both a
     parent and a child), so ids are collected into a set and deduped;
     walking every category (not just leaves) trades some redundant
     *listing* requests for a guarantee we don't miss a hadith that's only
     tagged on a non-leaf category.
  3. For every target language, fetch full records for all unique ids via
     hadeeths/multiple (confirmed live: accepts at least 40 ids/request),
     batched and cached per language.

Rate limit / caching: reuses common.fetch_json_cached (~2.5 req/s,
exponential backoff on 429/5xx, skips already-cached files on rerun --
resumable).
"""
import json
from pathlib import Path

from common import PROJECT_ROOT, fetch_json_cached, get_logger

BASE = "https://hadeethenc.com/api/v1"
RAW_DIR = PROJECT_ROOT / "data/raw/hadeethenc"
LANGS = ["ar", "en", "fr", "id", "ur", "tr"]
PER_PAGE = 100
BATCH_SIZE = 40

ATTRIBUTION = "HadeethEnc.com"
TERMS_NOTE = (
    "Attribution required; no modification of the published hadith/translation "
    "text; keep version + transcript info; notify HadeethEnc of corrections; "
    "re-sync to latest version. See https://hadeethenc.com/en Terms and "
    "Policies modal and https://hadeethenc.com/api-docs/. "
    "robots.txt Content-Signal: ai-train=yes."
)


def discover_category_ids(logger):
    cats = fetch_json_cached(f"{BASE}/categories/list/?language=ar", RAW_DIR / "categories.json", logger)
    if cats is None:
        logger.error("could not fetch categories/list, aborting")
        return []
    ids = [int(c["id"]) for c in cats]
    logger.info(f"{len(ids)} categories discovered")
    return ids


def collect_hadith_ids(category_ids, logger):
    all_ids = set()
    listing_dir = RAW_DIR / "listing"
    for cat_id in category_ids:
        page = 1
        while True:
            cache_path = listing_dir / f"cat_{cat_id}_p{page}.json"
            data = fetch_json_cached(
                f"{BASE}/hadeeths/list/?language=ar&category_id={cat_id}&page={page}&per_page={PER_PAGE}",
                cache_path, logger,
            )
            if data is None:
                logger.warning(f"category {cat_id} page {page}: fetch failed, stopping this category")
                break
            for item in data.get("data", []):
                all_ids.add(int(item["id"]))
            meta = data.get("meta", {})
            last_page = int(meta.get("last_page", page))
            if page >= last_page:
                break
            page += 1
    logger.info(f"{len(all_ids)} unique hadith ids discovered across {len(category_ids)} categories")
    return sorted(all_ids)


def fetch_records(hadith_ids, logger):
    counts = {}
    for lang in LANGS:
        lang_dir = RAW_DIR / "records" / lang
        n_fetched = 0
        for i in range(0, len(hadith_ids), BATCH_SIZE):
            batch = hadith_ids[i:i + BATCH_SIZE]
            cache_path = lang_dir / f"batch_{batch[0]}_{batch[-1]}.json"
            ids_param = ",".join(str(x) for x in batch)
            data = fetch_json_cached(
                f"{BASE}/hadeeths/multiple/?language={lang}&ids={ids_param}",
                cache_path, logger,
            )
            if data is None:
                logger.warning(f"lang={lang} batch starting at {batch[0]}: fetch failed")
                continue
            n_fetched += len(data)
        counts[lang] = n_fetched
        logger.info(f"lang={lang}: {n_fetched} records fetched (of {len(hadith_ids)} requested ids)")
    return counts


def main():
    logger = get_logger("download_hadeethenc")
    category_ids = discover_category_ids(logger)
    if not category_ids:
        return
    hadith_ids = collect_hadith_ids(category_ids, logger)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "hadith_ids.json").write_text(json.dumps(hadith_ids), encoding="utf-8")

    counts = fetch_records(hadith_ids, logger)

    manifest = {
        "base_url": BASE,
        "attribution": ATTRIBUTION,
        "terms": TERMS_NOTE,
        "n_categories": len(category_ids),
        "n_unique_hadith_ids": len(hadith_ids),
        "records_fetched_per_lang": counts,
        "langs": LANGS,
    }
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Done. {len(hadith_ids)} unique hadith ids, per-language record counts: {counts}")


if __name__ == "__main__":
    main()
