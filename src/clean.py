"""
Build data/processed/cleaned.jsonl from the raw fawazahmed0 Quran + Hadith
caches and the HadeethEnc cache: normalize Arabic, strip markup, detect
Quran quotes inside hadith text, filter bad pairs, and record everything
dropped for the report.

Run after download_quran.py, download_hadith.py, and download_hadeethenc.py.
(OPUS is deliberately NOT loaded here -- see download_opus.py's docstring
and PLAN.md section 8.2 for why its Tanzil corpus isn't training-ready.)
"""
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger
from download_quran import APPROVED_EDITION_KEYS, TARGET_LANGS as Q_LANGS
from download_hadith import TARGET_LANGS as H_LANGS

QURAN_RAW = PROJECT_ROOT / "data/raw/fawazahmed0_quran"
HADITH_RAW = PROJECT_ROOT / "data/raw/fawazahmed0_hadith"
HADEETHENC_RAW = PROJECT_ROOT / "data/raw/hadeethenc"
HADEETHENC_TGT_LANGS = ["en", "fr", "id", "ur", "tr"]
HADEETHENC_LICENSE = (
    "HadeethEnc.com; attribution required, no modification of the "
    "published text, keep version/transcript info -- see PLAN.md section 8.1"
)
OUT_DIR = PROJECT_ROOT / "data/processed"

TASHKEEL_RE = re.compile(
    "[ؐ-ًؚ-ٰٟۖ-ۭࣔ-ࣣ࣡-ࣿ]"
)
TATWEEL_RE = re.compile("ـ")
ALEF_VARIANTS_RE = re.compile("[أإآ]")  # أ إ آ -> ا
ARABIC_SCRIPT_RE = re.compile(r"[؀-ۿ]")
LATIN_OR_OTHER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
FOOTNOTE_MARKER_RE = re.compile(r"\[\s*\d+\s*\]|\(\s*\d+\s*\)")

LENGTH_RATIO_BOUNDS = {  # (min tgt/ar char-length ratio, max), generic default overridden after calibration
    "en": (0.25, 3.0),
    "fr": (0.25, 3.0),
    "id": (0.25, 3.0),
    "ur": (0.15, 3.0),  # Urdu/Arabic share script family & can render shorter
    "tr": (0.25, 3.0),
}


def strip_diacritics_tatweel(text: str) -> str:
    text = TASHKEEL_RE.sub("", text)
    text = TATWEEL_RE.sub("", text)
    return text


def normalize_alef(text: str) -> str:
    return ALEF_VARIANTS_RE.sub("ا", text)


def to_ar(diacritized: str) -> str:
    """ar field: diacritics/tatweel removed, alef variants unified."""
    return normalize_alef(strip_diacritics_tatweel(diacritized)).strip()


def to_ar_normalized(ar: str) -> str:
    """Extra, more aggressive normalization: additionally unify ى -> ي."""
    return ar.replace("ى", "ي")


def strip_markup(text: str) -> str:
    text = HTML_TAG_RE.sub(" ", text)
    text = FOOTNOTE_MARKER_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def arabic_script_ratio(text: str) -> float:
    letters = LATIN_OR_OTHER_RE.findall(text)
    if not letters:
        return 0.0
    arabic = ARABIC_SCRIPT_RE.findall(text)
    return len(arabic) / max(1, len(letters) + len(arabic))


class QuranQuoteIndex:
    """Signature-based near-substring matcher: avoids O(hadiths x verses) full scans."""

    def __init__(self, verses):
        # verses: list of (ref, ar_normalized_text)
        self.exact = {}
        self.sig_to_refs = defaultdict(list)
        self.verse_text = {}
        for ref, text in verses:
            self.exact[text] = ref
            self.verse_text[ref] = text
            words = text.split()
            if len(words) >= 5:
                sig = tuple(words[:5])
                self.sig_to_refs[sig].append(ref)

    def match(self, text: str):
        """Return (is_exact_duplicate, [matched_refs]) for a normalized text."""
        if text in self.exact:
            return True, [self.exact[text]]
        words = text.split()
        matches = set()
        for i in range(0, max(0, len(words) - 4)):
            sig = tuple(words[i:i + 5])
            for ref in self.sig_to_refs.get(sig, []):
                if self.verse_text[ref] in text:
                    matches.add(ref)
        return False, sorted(matches)


def load_quran_pairs(logger):
    manifest = json.loads((QURAN_RAW / "manifest.json").read_text(encoding="utf-8"))
    diac_file = QURAN_RAW / "editions" / f"{manifest['arabic']['diacritized']['file']}"
    diac = {(v["chapter"], v["verse"]): v["text"] for v in json.loads(diac_file.read_text(encoding="utf-8"))["quran"]}

    pairs = []
    ar_index = []  # for quran-quote detection
    for cv, text in diac.items():
        ar = to_ar(text)
        ar_index.append((f"quran:{cv[0]}:{cv[1]}", to_ar_normalized(ar)))

    for key, info in manifest["translations"].items():
        if not info["approved"]:
            continue
        fpath = QURAN_RAW / "editions" / info["file"]
        verses = json.loads(fpath.read_text(encoding="utf-8"))["quran"]
        for v in verses:
            cv = (v["chapter"], v["verse"])
            if cv not in diac:
                continue
            ar_diacritized = diac[cv]
            ar = to_ar(ar_diacritized)
            tgt = strip_markup(v["text"])
            license_note = info.get("license_note") or "source approved as government/waqf body"
            pairs.append({
                "id": f"quran:{cv[0]}:{cv[1]}:{info['lang']}",
                "source": "fawazahmed0_quran-api",
                "domain": "quran",
                "ref": f"quran:{cv[0]}:{cv[1]}",
                "ar_diacritized": ar_diacritized,
                "ar": ar,
                "ar_normalized": to_ar_normalized(ar),
                "lang": "ar",
                "tgt": tgt,
                "tgt_lang": info["lang"],
                "license": f"Unlicense (aggregator); translator={info['author']}; {license_note}",
            })
    logger.info(f"Quran: {len(pairs)} candidate pairs from {sum(1 for v in manifest['translations'].values() if v['approved'])} approved editions")
    return pairs, ar_index


def load_hadith_pairs(logger):
    manifest = json.loads((HADITH_RAW / "manifest.json").read_text(encoding="utf-8"))
    pairs = []
    for book, entry in manifest["books"].items():
        ar_path = HADITH_RAW / "editions" / entry["arabic"]["file"]
        ar_hadiths = {h["hadithnumber"]: h for h in json.loads(ar_path.read_text(encoding="utf-8"))["hadiths"]}

        for lang, tinfo in entry["translations"].items():
            tpath = HADITH_RAW / "editions" / tinfo["file"]
            t_hadiths = json.loads(tpath.read_text(encoding="utf-8"))["hadiths"]
            for h in t_hadiths:
                num = h["hadithnumber"]
                ar_h = ar_hadiths.get(num)
                if ar_h is None:
                    continue  # aligned by hadithnumber, not position -- skip unmatched
                ar_diacritized = strip_markup(ar_h["text"])
                ar = to_ar(ar_diacritized)
                tgt = strip_markup(h["text"])
                pairs.append({
                    "id": f"hadith:{book}:{num}:{lang}",
                    "source": "fawazahmed0_hadith-api",
                    "domain": "hadith",
                    "ref": f"hadith:{book}:{num}",
                    "ar_diacritized": ar_diacritized,
                    "ar": ar,
                    "ar_normalized": to_ar_normalized(ar),
                    "lang": "ar",
                    "tgt": tgt,
                    "tgt_lang": lang,
                    "license": f"Unlicense (aggregator); translator={tinfo['author']}; original translator copyright not independently confirmed, see PLAN.md",
                })
    logger.info(f"Hadith: {len(pairs)} candidate pairs from {len(manifest['books'])} books")
    return pairs


def load_hadeethenc_pairs(logger):
    records_dir = HADEETHENC_RAW / "records"
    if not records_dir.exists():
        logger.warning("no HadeethEnc raw data found (run download_hadeethenc.py first), skipping")
        return []

    pairs = []
    extra_text_fields = ["explanation", "hints", "grade", "attribution"]
    for lang in HADEETHENC_TGT_LANGS:
        lang_dir = records_dir / lang
        if not lang_dir.exists():
            logger.warning(f"hadeethenc: no cached records for lang={lang}, skipping")
            continue
        n = 0
        for batch_file in sorted(lang_dir.glob("batch_*.json")):
            batch = json.loads(batch_file.read_text(encoding="utf-8"))
            for rec in batch:
                ar_diacritized = strip_markup(rec.get("hadeeth_ar") or "")
                tgt = strip_markup(rec.get("hadeeth") or "")
                if not ar_diacritized or not tgt:
                    continue
                ar = to_ar(ar_diacritized)
                pair = {
                    "id": f"hadeethenc:{rec['id']}:{lang}",
                    "source": "hadeethenc",
                    "domain": "hadith",
                    "ref": f"hadeethenc:{rec['id']}",
                    "ar_diacritized": ar_diacritized,
                    "ar": ar,
                    "ar_normalized": to_ar_normalized(ar),
                    "lang": "ar",
                    "tgt": tgt,
                    "tgt_lang": lang,
                    "license": HADEETHENC_LICENSE,
                }
                for field in extra_text_fields:
                    val = rec.get(field)
                    if field == "hints":
                        val = [strip_markup(h) for h in (val or []) if h and h.strip()]
                    elif isinstance(val, str):
                        val = strip_markup(val)
                    if val:
                        pair[field] = val

                    ar_field = f"{field}_ar"
                    ar_val = rec.get(ar_field)
                    if ar_field == "hints_ar":
                        ar_val = [strip_markup(h) for h in (ar_val or []) if h and h.strip()]
                    elif isinstance(ar_val, str):
                        ar_val = strip_markup(ar_val)
                    if ar_val:
                        pair[ar_field] = ar_val
                pairs.append(pair)
                n += 1
        logger.info(f"hadeethenc/{lang}: {n} pairs loaded")
    logger.info(f"HadeethEnc: {len(pairs)} candidate pairs across {len(HADEETHENC_TGT_LANGS)} languages")
    return pairs


def filter_and_tag(pairs, quran_index, logger):
    drop_counts = defaultdict(int)
    dropped = []
    kept = []

    def drop(p, reason):
        drop_counts[reason] += 1
        dropped.append({
            "id": p["id"], "ref": p["ref"], "domain": p["domain"], "tgt_lang": p["tgt_lang"],
            "reason": reason,
            "ar_snippet": p["ar"][:120], "tgt_snippet": p["tgt"][:120],
        })

    # pass 1: quran-quote tagging + hard filters (empty, identical, wrong script)
    survivors = []
    for p in pairs:
        if not p["ar"].strip() or not p["tgt"].strip():
            drop(p, "empty_side")
            continue
        if p["ar"].strip() == p["tgt"].strip():
            drop(p, "identical_source_target")
            continue
        # Urdu is written in Perso-Arabic script and shares the ؀-ۿ
        # Unicode block with Arabic, so the Arabic-script heuristic below
        # would misfire on every correct Urdu pair -- only apply it to
        # target languages that should be pure Latin script.
        if p["tgt_lang"] != "ur":
            script_ratio = arabic_script_ratio(p["tgt"])
            if script_ratio > 0.3:
                drop(p, "wrong_script_target")
                continue

        if p["domain"] == "hadith":
            is_dup, matched = quran_index.match(p["ar_normalized"])
            if is_dup:
                drop(p, "hadith_is_pure_quran_quote_dedup")
                continue
            if matched:
                p["quran_quote_refs"] = matched
        survivors.append(p)

    # pass 2: per-language length-ratio calibration
    ratios_by_lang = defaultdict(list)
    for p in survivors:
        r = len(p["tgt"]) / max(1, len(p["ar"]))
        p["_ratio"] = r
        ratios_by_lang[p["tgt_lang"]].append(r)

    bounds = {}
    for lang, ratios in ratios_by_lang.items():
        median = statistics.median(ratios)
        lo, hi = LENGTH_RATIO_BOUNDS.get(lang, (0.25, 3.0))
        # widen/narrow generic bounds around the observed median, but never
        # tighter than the generic floor/ceiling
        bounds[lang] = (min(lo, median * 0.2), max(hi, median * 4.0))
        logger.info(f"lang={lang} median_ratio={median:.2f} n={len(ratios)} bounds={bounds[lang]}")

    for p in survivors:
        lo, hi = bounds[p["tgt_lang"]]
        if not (lo <= p["_ratio"] <= hi):
            drop(p, "length_ratio_outlier")
            continue
        del p["_ratio"]
        kept.append(p)

    return kept, drop_counts, dropped


def main():
    logger = get_logger("clean")
    quran_pairs, ar_verse_index = load_quran_pairs(logger)
    hadith_pairs = load_hadith_pairs(logger)
    hadeethenc_pairs = load_hadeethenc_pairs(logger)
    quran_index = QuranQuoteIndex(ar_verse_index)

    all_pairs = quran_pairs + hadith_pairs + hadeethenc_pairs
    kept, drop_counts, dropped = filter_and_tag(all_pairs, quran_index, logger)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "cleaned.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in kept:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    dropped_path = OUT_DIR / "dropped.jsonl"
    with dropped_path.open("w", encoding="utf-8") as f:
        for d in dropped:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    logger.info(f"Wrote {len(kept)} pairs to {out_path}, {len(dropped)} dropped items to {dropped_path}")
    logger.info(f"Drop reasons: {dict(drop_counts)}")
    (OUT_DIR / "drop_counts.json").write_text(json.dumps(drop_counts, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
