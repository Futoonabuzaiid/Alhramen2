"""
Download + verify OPUS's "Tanzil" corpus for ar-{en,fr,id,ur,tr} (Moses
format zips from https://object.pouta.csc.fi/OPUS-Tanzil/v1/moses/, listed
live via the official https://opus.nlpl.eu/opusapi/ endpoint).

IMPORTANT -- this script deliberately does NOT feed its output into
clean.py / the training pipeline. It downloads, caches, and inspects the
corpus, and writes a verification report explaining why. Two problems were
found by actually reading the extracted text (not just trusting the corpus
name), both confirmed for all 5 language pairs via each zip's `.ids` file:

  1. **The Arabic side is not Quran verse text.** Every pair's `.ids` file
     tags the Arabic column as `ar/jalalayn.xml.gz` -- that is Tafsir
     al-Jalalayn, a verse-by-verse *commentary*, not the Quran text itself.
     Reading the actual lines confirms this (e.g. verse 1:2's "Arabic" line
     is a grammatical explanation of the word "al-hamd", not the ayah).
     Using this column as the Arabic source in an Arabic->target training
     pair would silently train on (commentary, translation-of-a-different-
     verse-text) pairs, not (verse, translation) pairs.
  2. **License is non-commercial-only.** The corpus's own README
     (https://object.pouta.csc.fi/OPUS-Tanzil/v1/moses/README) states:
     "The translations provided at this page are for non-commercial
     purposes only." This is a harder restriction than HadeethEnc's
     (attribution-only) and was not something we could see before actually
     fetching the file live.

Given both issues, and that the *target*-language translators here
(ahmedali, hamidullah, indonesian, ates -- read from each `.ids` file) are
individually-authored editions of the same class already excluded from our
approved Quran set in download_quran.py (not attributed to a government/
waqf body), this corpus is not integrated into cleaned.jsonl. It is kept
as cached raw data + this report in case you want to revisit it -- e.g. by
re-pairing its target-language column (aligned by sura:ayah in the `.ids`
file) against our own verified fawazahmed0/quran-api Arabic text instead of
trusting OPUS's "ar" column, after weighing the non-commercial restriction.

Total download for all 5 pairs is ~65MB (well under the "few hundred MB"
threshold), so this runs without extra approval.
"""
import json
import zipfile
from pathlib import Path

from common import PROJECT_ROOT, fetch_json_cached, fetch_binary_cached, get_logger

OPUSAPI = "https://opus.nlpl.eu/opusapi/"
RAW_DIR = PROJECT_ROOT / "data/raw/opus_tanzil"
TARGET_LANGS = ["en", "fr", "id", "ur", "tr"]

LICENSE_NOTE = (
    "OPUS-Tanzil README (https://object.pouta.csc.fi/OPUS-Tanzil/v1/moses/README): "
    "'The translations provided at this page are for non-commercial purposes only.'"
)
AR_SIDE_WARNING = (
    "The Arabic column in this corpus is Tafsir al-Jalalayn commentary "
    "(ar/jalalayn.xml.gz per the .ids file), NOT Quran verse text. "
    "Do not use it as an Arabic source for verse<->translation pairs."
)


def find_corpus_url(pair_json, tgt_lang, logger):
    for c in pair_json.get("corpora", []):
        if c["corpus"] == "Tanzil":
            return c["url"], c
    logger.error(f"no Tanzil corpus found for ar-{tgt_lang}")
    return None, None


def inspect_zip(zip_path: Path, pair: str):
    z = zipfile.ZipFile(zip_path)
    names = z.namelist()
    ar_name = next(n for n in names if n.endswith(f".{pair.split('-')[0]}"))
    tgt_name = next(n for n in names if n.endswith(f".{pair.split('-')[1]}"))
    ids_name = next(n for n in names if n.endswith(".ids"))

    ar_lines = z.read(ar_name).decode("utf-8").splitlines()
    tgt_lines = z.read(tgt_name).decode("utf-8").splitlines()
    ids_lines = z.read(ids_name).decode("utf-8").splitlines()

    first_id_fields = ids_lines[0].split("\t") if ids_lines else []
    ar_tag = first_id_fields[0] if len(first_id_fields) > 0 else "?"
    tgt_tag = first_id_fields[1] if len(first_id_fields) > 1 else "?"

    return {
        "n_lines": len(ar_lines),
        "ar_side_tag": ar_tag,
        "tgt_side_tag": tgt_tag,
        "sample_ar": ar_lines[1] if len(ar_lines) > 1 else "",
        "sample_tgt": tgt_lines[1] if len(tgt_lines) > 1 else "",
        "sample_ref": first_id_fields[2] if len(first_id_fields) > 2 else "",
    }


def main():
    logger = get_logger("download_opus")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    report = {"license": LICENSE_NOTE, "ar_side_warning": AR_SIDE_WARNING, "pairs": {}, "integrated_into_pipeline": False}

    for tgt in TARGET_LANGS:
        pair = f"ar-{tgt}"
        listing = fetch_json_cached(
            f"{OPUSAPI}?source=ar&target={tgt}&preprocessing=moses",
            RAW_DIR / f"opusapi_ar-{tgt}.json", logger,
        )
        if listing is None:
            logger.error(f"{pair}: could not list corpora, skipping")
            continue
        url, corpus_meta = find_corpus_url(listing, tgt, logger)
        if url is None:
            continue

        zip_path = RAW_DIR / f"{pair}.txt.zip"
        ok = fetch_binary_cached(url, zip_path, logger)
        if not ok:
            logger.error(f"{pair}: download failed")
            continue

        info = inspect_zip(zip_path, pair)
        info["alignment_pairs_reported_by_opusapi"] = corpus_meta["alignment_pairs"]
        report["pairs"][pair] = info
        logger.info(f"{pair}: {info['n_lines']} lines, ar_side_tag={info['ar_side_tag']}, tgt_side_tag={info['tgt_side_tag']}")

    (RAW_DIR / "verification_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        "Done. Cached + inspected OPUS-Tanzil for all 5 pairs. NOT integrated into "
        "clean.py -- see verification_report.json and this file's module docstring "
        "for why (Arabic column is tafsir, not verse text; non-commercial license)."
    )


if __name__ == "__main__":
    main()
