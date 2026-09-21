"""
Download Hadith Arabic + target-language translations from fawazahmed0/hadith-api
(verified live: raw.githubusercontent.com/fawazahmed0/hadith-api/1/..., Unlicense).

Caches raw edition JSON under data/raw/fawazahmed0_hadith/editions/.
Writes data/raw/fawazahmed0_hadith/manifest.json linking each book's Arabic
edition to its per-language translation editions (verified index-aligned by
'hadithnumber').

License note: unlike Quran, none of these translations are attributed to a
government/waqf body in the metadata -- they are individually-authored
classical hadith translations (Muhsin Khan, etc.) that have circulated freely
via Islamic educational platforms (this project's own upstream is sunnah.com)
for decades. We include them but record the translator name in every pair's
license field so this can be audited/revisited, per PLAN.md.
"""
import json
from pathlib import Path

from common import PROJECT_ROOT, fetch_json_cached, get_logger

BASE = "https://raw.githubusercontent.com/fawazahmed0/hadith-api/1"
RAW_DIR = PROJECT_ROOT / "data/raw/fawazahmed0_hadith"
TARGET_LANGS = {"eng": "en", "fra": "fr", "ind": "id", "urd": "ur", "tur": "tr"}


def pick_best(names):
    """Prefer the edition name without a trailing digit suffix (the '1','2' variants
    are usually alternate/duplicate renderings of the same translation)."""
    plain = [n for n in names if not n[-1].isdigit()]
    return sorted(plain)[0] if plain else sorted(names)[0]


def main():
    logger = get_logger("download_hadith")
    logger.info("Fetching editions.json")
    editions = fetch_json_cached(f"{BASE}/editions.json", RAW_DIR / "editions.json", logger)
    if editions is None:
        logger.error("Could not fetch editions.json, aborting")
        return

    manifest = {"books": {}}

    for book, info in editions.items():
        collection = info["collection"]
        by_key = {ed["name"]: ed for ed in collection}

        arabic_names = [ed["name"] for ed in collection if ed["language"] == "Arabic"
                         and "removed" not in (ed.get("comments") or "").lower()]
        if not arabic_names:
            arabic_names = [ed["name"] for ed in collection if ed["language"] == "Arabic"]
        if not arabic_names:
            logger.warning(f"{book}: no Arabic edition, skipping book")
            continue
        arabic_name = pick_best(arabic_names)

        ar_fname = f"{arabic_name}.json"
        ar_data = fetch_json_cached(f"{BASE}/editions/{ar_fname}", RAW_DIR / "editions" / ar_fname, logger)
        if ar_data is None:
            logger.error(f"{book}: failed to fetch Arabic edition {arabic_name}")
            continue

        book_entry = {"arabic": {"name": arabic_name, "file": ar_fname, "hadiths": len(ar_data["hadiths"])},
                      "translations": {}}

        for prefix, code in TARGET_LANGS.items():
            names = [n for n in by_key if n.startswith(prefix + "-")]
            if not names:
                continue
            name = pick_best(names)
            fname = f"{name}.json"
            data = fetch_json_cached(f"{BASE}/editions/{fname}", RAW_DIR / "editions" / fname, logger)
            if data is None:
                logger.error(f"{book}/{name}: fetch failed")
                continue
            n_hadiths = len(data["hadiths"])
            if n_hadiths != book_entry["arabic"]["hadiths"]:
                logger.warning(
                    f"{book}/{name}: count mismatch ar={book_entry['arabic']['hadiths']} tgt={n_hadiths} "
                    "(will align by hadithnumber, not position, in clean.py)"
                )
            book_entry["translations"][code] = {
                "name": name,
                "file": fname,
                "author": by_key[name].get("author", ""),
                "hadiths": n_hadiths,
            }

        manifest["books"][book] = book_entry

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    for book, entry in manifest["books"].items():
        missing = set(TARGET_LANGS.values()) - set(entry["translations"])
        if missing:
            logger.info(f"{book}: missing languages {sorted(missing)}")
    logger.info(f"Done. {len(manifest['books'])} books cached.")


if __name__ == "__main__":
    main()
