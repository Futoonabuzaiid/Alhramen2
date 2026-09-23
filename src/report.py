"""
Build reports/data_report.md and reports/samples/<source>_<lang>.csv (50
random pairs per source/language) from data/processed/cleaned.jsonl and
data/processed/dropped.jsonl.
"""
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger

CLEANED = PROJECT_ROOT / "data/processed/cleaned.jsonl"
DROPPED = PROJECT_ROOT / "data/processed/dropped.jsonl"
REPORTS_DIR = PROJECT_ROOT / "reports"
SAMPLES_DIR = REPORTS_DIR / "samples"
BASELINE_BLEU_JSON = REPORTS_DIR / "baseline_bleu_results.json"
SEED = 20260101


def word_count(s: str) -> int:
    return len(s.split())


def percentile(sorted_vals, p):
    """Nearest-rank percentile, 0 <= p <= 100, sorted_vals non-empty."""
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, max(0, int(round(p / 100 * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


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
    lines.append("")

    # --- hadith Arabic word-count percentiles (for prepare_for_training.py's
    # length rule -- see src/prepare_for_training.py and PLAN.md) ---
    hadith_word_counts_by_source = defaultdict(list)
    hadith_word_counts_all = []
    for r in rows:
        if r["domain"] != "hadith":
            continue
        n = word_count(r["ar"])
        hadith_word_counts_all.append(n)
        hadith_word_counts_by_source[r["source"]].append(n)

    lines.append("## Hadith Arabic word-count percentiles")
    lines.append("")
    lines.append("Word counts (whitespace-split, not tokenizer counts) on the `ar` field, "
                  "one row per (hadith, target-language) pair -- so a hadith with 5 translations "
                  "is counted 5 times, weighting by how often that length appears in training data.")
    lines.append("")
    lines.append("| source | n | p50 | p90 | p99 | max |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for source in sorted(hadith_word_counts_by_source):
        vals = sorted(hadith_word_counts_by_source[source])
        lines.append(f"| {source} | {len(vals)} | {percentile(vals, 50)} | {percentile(vals, 90)} | "
                      f"{percentile(vals, 99)} | {vals[-1]} |")
    all_sorted = sorted(hadith_word_counts_all)
    lines.append(f"| **all hadith** | {len(all_sorted)} | {percentile(all_sorted, 50)} | "
                  f"{percentile(all_sorted, 90)} | {percentile(all_sorted, 99)} | {all_sorted[-1]} |")
    lines.append("")
    lines.append("See `src/prepare_for_training.py` for the actual NLLB-tokenizer-based length rule "
                  "(targets ~128 tokens, not words) applied on top of this data; its own report covers "
                  "how many pairs were split/truncated/left as-is.")

    # --- baseline BLEU (from src/baseline_bleu.py, if it's been run) ---
    if BASELINE_BLEU_JSON.exists():
        bb = json.loads(BASELINE_BLEU_JSON.read_text(encoding="utf-8"))
        lines.append("")
        lines.append("## Baseline BLEU")
        lines.append("")
        mode = "full valid split" if not bb["max_examples"] else f"domain-stratified sample, seed={bb['seed']}"
        lines.append(f"`facebook/nllb-200-distilled-600M`, zero-shot (no fine-tuning). "
                      f"max_examples={bb['max_examples'] or 'full split'} ({mode}), "
                      f"batch_size={bb['batch_size']}. Raw results: `reports/baseline_bleu_results.json`.")
        lines.append("")
        lines.append("| ar -> tgt | n | of full valid split | sacreBLEU | seconds |")
        lines.append("|---|---:|---:|---:|---:|")
        for lang, r in bb["languages"].items():
            lines.append(f"| ar-{lang} | {r['n']} | {r['n_full_valid_split']} | {r['bleu']:.2f} | {r['seconds']:.0f} |")
        lines.append("")
        lines.append("| ar -> tgt | domain | n | sacreBLEU |")
        lines.append("|---|---|---:|---:|")
        for lang, r in bb["languages"].items():
            for domain, d in sorted(r["by_domain"].items()):
                lines.append(f"| ar-{lang} | {domain} | {d['n']} | {d['bleu']:.2f} |")

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
    lines.append("- **OPUS's TED2020 corpus was checked and not built**: its Usage Policy is "
                  "No-Derivatives ('you cannot edit, remix, create, modify or alter the form... in any "
                  "way'), with no research/ML carve-out -- judged not clearly compatible with training "
                  "use. bible-uedin (CC0, fully unrestricted) was also found but is out of this "
                  "pipeline's requested scope (Bible text, not Islamic). See PLAN.md section 8.11.")
    lines.append("- **37.4% of training pairs get truncated at the ~128-token length rule** "
                  "(`src/prepare_for_training.py`): 120,044 as-is, 208 split, 71,811 truncated, out of "
                  "192,063 input pairs. Truncation is lossy (cuts mid-sentence); the low split rate "
                  "(0.1%) means most over-length pairs don't have a clean 1:1 sentence-count match "
                  "between Arabic and the target language. See the hadith word-count percentiles above "
                  "-- p99 is 270+ words, and some outliers reach ~1,900 words (full isnad chains), which "
                  "is what drives this.")

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
