"""
Baseline MT quality check: run facebook/nllb-200-distilled-600M zero-shot
on data/processed/valid.ar_<lang>.jsonl for each of the 5 target languages
and report sacreBLEU per pair.

DOWNLOAD WARNING: the first run of this script downloads the NLLB-200
distilled 600M model (~2.4GB) from Hugging Face. Do not run this without
the user's explicit go-ahead (see PLAN.md) -- this is separate from, and
much larger than, the tokenizer-only download in prepare_for_training.py.

Runs on CPU if no GPU is available (this machine has CPU-only torch as of
this writing). CPU generation is slow, and the full valid split
(2000-2300 pairs per language x 5 languages) is majority hadith/hadeethenc
domain, whose text is 2.5-4.6x longer than Quran text -- a smoke test on
the first N rows of each file is NOT representative, since clean.py writes
Quran pairs first (see PLAN.md's baseline_bleu section for the measured
gap between a quran-only sample and a domain-representative one).

Sampling (--max-examples N, N>0): stratified by domain, proportional to
each domain's share of the full valid split for that language pair, with
a fixed --seed for reproducibility. This is the default and recommended
mode for anything short of the full split.
Full split: --max-examples 0 uses every row, no sampling.

Usage:
    python src/baseline_bleu.py                        # 200/language, stratified by domain
    python src/baseline_bleu.py --max-examples 400      # larger stratified sample
    python src/baseline_bleu.py --max-examples 0        # full valid split, slow on CPU
    python src/baseline_bleu.py --langs en fr           # only these language pairs

Writes reports/baseline_bleu.md (standalone) and
reports/baseline_bleu_results.json (raw results -- src/report.py reads
this, if present, to add a "Baseline BLEU" section to data_report.md).
"""
import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger

MODEL_NAME = "facebook/nllb-200-distilled-600M"
NLLB_LANG_CODES = {
    "ar": "arb_Arab",
    "en": "eng_Latn",
    "fr": "fra_Latn",
    "id": "ind_Latn",
    "ur": "urd_Arab",
    "tr": "tur_Latn",
}
ALL_TGT_LANGS = ["en", "fr", "id", "ur", "tr"]
VALID_DIR = PROJECT_ROOT / "data/processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
BATCH_SIZE = 8
MAX_NEW_TOKENS = 200
SEED = 20260101


def load_all_valid_pairs(tgt_lang: str):
    path = VALID_DIR / f"valid.ar_{tgt_lang}.jsonl"
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def stratified_sample(rows, max_examples: int, seed: int):
    """Sample max_examples rows, proportional to each domain's share of `rows`."""
    by_domain = defaultdict(list)
    for r in rows:
        by_domain[r["domain"]].append(r)

    rng = random.Random(seed)
    total = len(rows)
    sampled = []
    remaining_budget = max_examples
    domains = sorted(by_domain)
    for i, domain in enumerate(domains):
        group = by_domain[domain]
        if i == len(domains) - 1:
            n = remaining_budget  # last domain takes whatever's left, avoids rounding loss
        else:
            n = round(max_examples * len(group) / total)
        n = min(n, len(group), remaining_budget)
        sampled.extend(rng.sample(group, n))
        remaining_budget -= n
    rng.shuffle(sampled)
    return sampled


def translate_batch(model, tokenizer, texts, tgt_code, device):
    tokenizer.src_lang = NLLB_LANG_CODES["ar"]
    enc = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=256).to(device)
    forced_bos = tokenizer.convert_tokens_to_ids(tgt_code)
    out = model.generate(**enc, forced_bos_token_id=forced_bos, max_new_tokens=MAX_NEW_TOKENS, num_beams=1)
    return tokenizer.batch_decode(out, skip_special_tokens=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-examples", type=int, default=200,
                         help="Examples per language pair, domain-stratified (0 = full valid split, no sampling).")
    parser.add_argument("--langs", nargs="+", default=ALL_TGT_LANGS, choices=ALL_TGT_LANGS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--save-samples", type=int, default=10,
                         help="Number of example (ar, hyp, ref) triples to save per language in the JSON output.")
    args = parser.parse_args()

    logger = get_logger("baseline_bleu")
    logger.warning(
        f"About to load {MODEL_NAME} (~2.4GB download on first run). "
        "This should only happen after explicit user approval."
    )

    import sacrebleu
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    json_path = REPORTS_DIR / "baseline_bleu_results.json"
    json_results = {"max_examples": args.max_examples, "seed": args.seed, "batch_size": args.batch_size,
                     "model": MODEL_NAME, "languages": {}}
    if json_path.exists():
        existing = json.loads(json_path.read_text(encoding="utf-8"))
        if existing.get("max_examples") == args.max_examples and existing.get("seed") == args.seed:
            json_results["languages"] = existing.get("languages", {})
            logger.info(f"Merging with existing results for: {list(json_results['languages'])}")
        else:
            logger.warning(
                f"Existing {json_path} has different max_examples/seed "
                f"({existing.get('max_examples')}/{existing.get('seed')} vs {args.max_examples}/{args.seed}) "
                "-- not merging, starting fresh for this invocation's languages."
            )

    results = {}
    per_domain_hyps = defaultdict(lambda: defaultdict(list))
    per_domain_refs = defaultdict(lambda: defaultdict(list))

    for tgt_lang in args.langs:
        all_rows = load_all_valid_pairs(tgt_lang)
        if not all_rows:
            logger.warning(f"{tgt_lang}: no valid rows found, skipping")
            continue
        if args.max_examples and args.max_examples > 0:
            rows = stratified_sample(all_rows, args.max_examples, args.seed)
        else:
            rows = all_rows
        domain_counts = defaultdict(int)
        for r in rows:
            domain_counts[r["domain"]] += 1
        logger.info(f"{tgt_lang}: sampled {len(rows)}/{len(all_rows)} rows, by domain: {dict(domain_counts)}")

        tgt_code = NLLB_LANG_CODES[tgt_lang]
        hyps, refs = [], []
        t0 = time.time()
        with torch.no_grad():
            for i in range(0, len(rows), args.batch_size):
                batch = rows[i:i + args.batch_size]
                texts = [r["ar"] for r in batch]
                out = translate_batch(model, tokenizer, texts, tgt_code, device)
                hyps.extend(out)
                refs.extend(r["tgt"] for r in batch)
                for r, h in zip(batch, out):
                    per_domain_hyps[tgt_lang][r["domain"]].append(h)
                    per_domain_refs[tgt_lang][r["domain"]].append(r["tgt"])
                if (i // args.batch_size) % 10 == 0:
                    logger.info(f"{tgt_lang}: {i + len(batch)}/{len(rows)} translated")

        bleu = sacrebleu.corpus_bleu(hyps, [refs])
        elapsed = time.time() - t0
        results[tgt_lang] = {"n": len(rows), "bleu": bleu.score, "seconds": elapsed}
        logger.info(f"{tgt_lang}: BLEU={bleu.score:.2f} on {len(rows)} pairs ({elapsed:.0f}s), "
                    f"domains={dict(domain_counts)}")

        by_domain_json = {}
        for domain, dhyps in per_domain_hyps[tgt_lang].items():
            drefs = per_domain_refs[tgt_lang][domain]
            dbleu = sacrebleu.corpus_bleu(dhyps, [drefs])
            by_domain_json[domain] = {"n": len(dhyps), "bleu": dbleu.score}

        n_samples = min(args.save_samples, len(rows))
        sample_idx = list(range(n_samples))
        json_results["languages"][tgt_lang] = {
            "n": len(rows),
            "n_full_valid_split": len(all_rows),
            "domain_counts_sampled": dict(domain_counts),
            "bleu": bleu.score,
            "seconds": elapsed,
            "by_domain": by_domain_json,
            "sample_translations": [
                {"ar": rows[i]["ar"], "domain": rows[i]["domain"], "hyp": hyps[i], "ref": refs[i]}
                for i in sample_idx
            ],
        }

    # Rebuild the standalone .md from the full merged set of languages (not just
    # this invocation's), so running one language at a time still leaves a
    # complete, up-to-date report after each run.
    all_langs = json_results["languages"]
    lines = ["# Baseline BLEU -- facebook/nllb-200-distilled-600M (zero-shot, no fine-tuning)", ""]
    mode = "full valid split" if not args.max_examples else f"domain-stratified sample, seed={args.seed}"
    lines.append(f"Evaluated on `data/processed/valid.ar_<lang>.jsonl`, "
                  f"max_examples={args.max_examples or 'full split'} ({mode}), batch_size={args.batch_size}.")
    lines.append("")
    lines.append("| ar -> tgt | n | of full valid split | sacreBLEU | seconds |")
    lines.append("|---|---:|---:|---:|---:|")
    for lang, r in all_langs.items():
        lines.append(f"| ar-{lang} | {r['n']} | {r['n_full_valid_split']} | {r['bleu']:.2f} | {r['seconds']:.0f} |")

    lines.append("")
    lines.append("## By domain")
    lines.append("")
    lines.append("| ar -> tgt | domain | n | sacreBLEU |")
    lines.append("|---|---|---:|---:|")
    for lang, r in all_langs.items():
        for domain, d in sorted(r["by_domain"].items()):
            lines.append(f"| ar-{lang} | {domain} | {d['n']} | {d['bleu']:.2f} |")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "baseline_bleu.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote {out_path}")

    json_path.write_text(json.dumps(json_results, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Wrote {json_path} (languages now in file: {list(all_langs)})")


if __name__ == "__main__":
    main()
