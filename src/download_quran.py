"""
Download Quran Arabic + target-language translations from fawazahmed0/quran-api
(verified live: raw.githubusercontent.com/fawazahmed0/quran-api/1/..., Unlicense).

Caches every raw edition JSON under data/raw/fawazahmed0_quran/editions/.
Writes data/raw/fawazahmed0_quran/manifest.json describing which editions
were fetched and which were classified as "approved" (clearly a government/
waqf body) vs "needs_approval" (individually-authored, possible independent
copyright) for use downstream in clean.py.
"""
import json
from pathlib import Path

from common import PROJECT_ROOT, fetch_json_cached, get_logger

BASE = "https://raw.githubusercontent.com/fawazahmed0/quran-api/1"
RAW_DIR = PROJECT_ROOT / "data/raw/fawazahmed0_quran"
TARGET_LANGS = {"eng": "en", "fra": "fr", "ind": "id", "urd": "ur", "tur": "tr"}

# Arabic editions used as source-of-truth text.
ARABIC_EDITIONS = {
    "diacritized": "ara_quranuthmanihaf",  # keeps diacritics -> ar_diacritized
    "plain": "ara_quransimple",  # used only to cross-check verse counts
}

# Editions whose 'author'/'source' clearly identifies a government or waqf
# body (per user decision: exclude individually-authored translations by
# default even though the repo's Unlicense covers the compilation itself),
# plus individually-approved exceptions the user has explicitly signed off
# on after reviewing the candidate list in sources.csv/PLAN.md.
APPROVED_EDITION_KEYS = {
    "eng_muhammadtaqiudd",  # Hilali-Khan, published/distributed by King Fahd Complex (Saudi govt)
    "ind_indonesianislam",  # Indonesian Ministry of Religious Affairs
    "ind_kingfahdcomplex",  # King Fahd Complex (Saudi govt)
    "tur_diyanetisleri",  # Diyanet Isleri (Turkey's Presidency of Religious Affairs, govt)
    "tur_diyanetvakfi",  # Diyanet Vakfi (Diyanet Foundation)
    "urd_muhammadtaqiusm",  # Muhammad Taqi Usmani -- individually-authored, explicitly approved by user (PLAN.md section 8.7).
                            # License status UNCONFIRMED: aggregator has no 'source' URL for this edition, and no
                            # citable public terms/license statement was found for it (see PLAN.md section 8.7).
    "fra_muhammadhamidul",  # Muhammad Hamidullah -- individually-authored, explicitly approved by user (PLAN.md section 8.8); non-commercial-only, see LICENSE_NOTES below
}

# Extra per-edition license text for approved-by-exception editions whose
# terms carry a restriction beyond the default gov/waqf-body assumption
# (verified live against the edition's own `source`, not guessed). Merged
# into the pair's `license` field in clean.py.
LICENSE_NOTES = {
    "fra_muhammadhamidul": (
        "Tanzil.net Terms of Use (https://tanzil.net/trans/, verified live): "
        "'The translations provided at this page are for non-commercial "
        "purposes only. If used otherwise, you need to obtain necessary "
        "permission from the translator or the publisher.' COMPLIANT: "
        "project's confirmed license basis (PLAN.md 'Project license "
        "basis', 2026-09-22) is non-commercial research/educational use, "
        "no revenue, no commercial deployment -- satisfies this "
        "restriction. Re-check if project scope ever becomes commercial."
    ),
}


def target_language_editions(editions: dict):
    """Return {edition_key: info} for non-transliteration editions in our 5 languages."""
    result = {}
    for prefix in TARGET_LANGS:
        for key, info in editions.items():
            if key.startswith(prefix + "_") and "_la" not in key:
                result[key] = info
    return result


def edition_filename(link: str) -> str:
    return link.rsplit("/", 1)[-1]


def main():
    logger = get_logger("download_quran")
    logger.info("Fetching editions.json")
    editions = fetch_json_cached(f"{BASE}/editions.json", RAW_DIR / "editions.json", logger)
    if editions is None:
        logger.error("Could not fetch editions.json, aborting")
        return

    manifest = {"arabic": {}, "translations": {}}

    for role, key in ARABIC_EDITIONS.items():
        info = editions[key]
        fname = edition_filename(info["link"])
        data = fetch_json_cached(f"{BASE}/editions/{fname}", RAW_DIR / "editions" / fname, logger)
        if data is None:
            logger.error(f"failed to fetch arabic edition {key}")
            continue
        manifest["arabic"][role] = {"key": key, "file": fname, "verses": len(data["quran"])}

    lang_editions = target_language_editions(editions)
    logger.info(f"Found {len(lang_editions)} target-language editions to fetch")

    for key, info in lang_editions.items():
        fname = edition_filename(info["link"])
        data = fetch_json_cached(f"{BASE}/editions/{fname}", RAW_DIR / "editions" / fname, logger)
        if data is None:
            logger.error(f"failed to fetch {key}")
            continue
        lang_prefix = key.split("_")[0]
        manifest["translations"][key] = {
            "file": fname,
            "lang": TARGET_LANGS[lang_prefix],
            "author": info.get("author", ""),
            "source": info.get("source", ""),
            "verses": len(data["quran"]),
            "approved": key in APPROVED_EDITION_KEYS,
            "license_note": LICENSE_NOTES.get(key, ""),
        }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    n_approved = sum(1 for v in manifest["translations"].values() if v["approved"])
    logger.info(f"Done. {len(manifest['translations'])} editions cached, {n_approved} approved for training use.")
    for lang_prefix, code in TARGET_LANGS.items():
        approved = [k for k, v in manifest["translations"].items() if v["lang"] == code and v["approved"]]
        if not approved:
            logger.warning(f"No approved (gov/waqf) Quran edition for lang={code} -- gap, see PLAN.md/report")


if __name__ == "__main__":
    main()
