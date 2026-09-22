"""
Build reports/data_report.md and reports/samples/<source>_<lang>.csv (50
random pairs per source/language) from data/processed/cleaned.jsonl and
data/processed/dropped.jsonl.
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger

CLEANED = PROJECT_ROOT / "data/processed/cleaned.jsonl"
DROPPED = PROJECT_ROOT / "data/processed/dropped.jsonl"
REPORTS_DIR = PROJECT_ROOT / "reports"
SAMPLES_DIR = REPORTS_DIR / "samples"
SEED = 20260101


def word_count(s: str) -> int:
    return len(s.split())


def main():
    logger = get_logger("report")
    random.seed(SEED)

    rows = []
    with CLEANED.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))

    dropped = []
    with DROPPED.open(encoding="utf-8") as f:
        for line in f:
            dropped.append(json.loads(line))

    # --- stats table: source x domain x tgt_lang ---
    stats = defaultdict(lambda: {"n": 0, "ar_words": 0, "tgt_words": 0})
    by_source_lang = defaultdict(list)
    for r in rows:
        key = (r["source"], r["domain"], r["tgt_lang"])
        s = stats[key]
        s["n"] += 1
        s["ar_words"] += word_count(r["ar"])
        s["tgt_words"] += word_count(r["tgt"])
        by_source_lang[(r["source"], r["tgt_lang"])].append(r)

    lines = ["# Data Report", "", f"Generated from {len(rows)} kept pairs, {len(dropped)} dropped pairs.", ""]
    lines.append("## Pairs by source x domain x target language")
    lines.append("")
    lines.append("| source | domain | tgt_lang | pairs | avg ar words | avg tgt words |")
    lines.append("|---|---|---|---:|---:|---:|")
    for (source, domain, lang), s in sorted(stats.items()):
        avg_ar = s["ar_words"] / s["n"]
        avg_tgt = s["tgt_words"] / s["n"]
        lines.append(f"| {source} | {domain} | {lang} | {s['n']} | {avg_ar:.1f} | {avg_tgt:.1f} |")

    # --- dropped items summary ---
    drop_by_reason = defaultdict(int)
    for d in dropped:
        drop_by_reason[d["reason"]] += 1
    lines.append("")
    lines.append("## Dropped items by reason")
    lines.append("")
    lines.append("| reason | count |")
    lines.append("|---|---:|")
    for reason, n in sorted(drop_by_reason.items(), key=lambda x: -x[1]):
        lines.append(f"| {reason} | {n} |")
    lines.append("")
    lines.append(f"Full list with source/target snippets: `data/processed/dropped.jsonl` ({len(dropped)} rows).")

    # --- known gaps (from PLAN.md decisions) ---
    lines.append("")
    lines.append("## Known gaps")
    lines.append("")
    lines.append("- **Quran domain has no approved French edition.** No fr Quran edition in "
                  "fawazahmed0/quran-api is attributed to a government/waqf body, so the Quran domain "
                  "currently contributes 0 pairs for fr. (Urdu's gap is closed: you approved Muhammad "
                  "Taqi Usmani's individually-authored translation -- see PLAN.md section 8.7.) Hadith "
                  "still covers fr. See `sources.csv` (fawazahmed0_quran-api row) for the full French "
                  "candidate list if you want to approve one.")
    lines.append("- **sharh/hints fields**: now included for the `hadeethenc` source (`explanation`, "
                  "`hints`, `grade`, `attribution` and their `_ar` counterparts, stored as extra fields "
                  "on each pair, not expanded into separate rows). See PLAN.md section 8.1.")
    lines.append("- **OPUS (Tanzil corpus) was downloaded and inspected but deliberately excluded**: its "
                  "Arabic column is Tafsir al-Jalalayn commentary, not Quran verse text, and its license "
                  "is non-commercial-only. See PLAN.md section 8.2.")
    lines.append("- **King Fahd Complex has no direct translation downloads for fr/ur/en/id/tr** "
                  "(checked read-only, nothing downloaded): its /quran-translations/ page lists 50+ "
                  "languages as plain text with no links at all, and doesn't even list French or "
                  "English. Its /quran-dev/ developer platform has real download links, but only for "
                  "Arabic text/commentary, not translations. fawazahmed0/quran-api remains the source "
                  "for these languages. See PLAN.md section 8.3.")
    lines.append("- **IslamHouse was verified but not scraped** -- it has a real public API, but book "
                  "content is PDF-only (no inline text). Its 'articles' type does have inline text on "
                  "some items (39.5% of a 200-item sample), but a full probe found the yield of usable "
                  "(Arabic + target-language, both with inline text) pairs is negligible -- at best a "
                  "handful per language. No content-reuse license was found beyond a visitor-privacy "
                  "policy either way. See PLAN.md sections 8.4 and 8.9.")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "data_report.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote {REPORTS_DIR / 'data_report.md'}")

    # --- 50 random samples per source/language ---
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for (source, lang), items in by_source_lang.items():
        sample = random.sample(items, min(50, len(items)))
        path = SAMPLES_DIR / f"{source}_{lang}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ref", "domain", "ar", "tgt", "tgt_lang", "license"])
            w.writeheader()
            for r in sample:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        logger.info(f"Wrote {path} ({len(sample)} samples)")


if __name__ == "__main__":
    main()
