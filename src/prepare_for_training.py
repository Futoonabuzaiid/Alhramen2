"""
Build data/processed/train_ready.jsonl from data/processed/train.jsonl by
applying a max-length rule targeting NLLB fine-tuning (~128 tokens/side,
counted with the actual NLLB-200 tokenizer, not a word-count heuristic).

Does NOT touch cleaned.jsonl or train.jsonl -- those stay the canonical,
untruncated record. This script only adds a derived, training-shaped file.

Rule per pair:
  1. Tokenize `ar` and `tgt` with the NLLB tokenizer. If both are
     <= MAX_TOKENS: keep as-is ("as_is").
  2. Otherwise, try splitting both `ar` and `tgt` into sentences on
     [.!?؟۔] boundaries. If the two sides produce the SAME number of
     sentences (>1) and every resulting per-sentence segment is
     <= MAX_TOKENS on both sides, emit one output pair per sentence,
     sharing the original `ref` but with a distinct `id`/`split_index`
     ("split"). This only works when sentence counts line up 1:1 --
     we do not attempt cross-lingual sentence realignment, since a
     wrong split would silently corrupt more pairs than it fixes.
  3. Otherwise, truncate both sides to MAX_TOKENS tokens (decoded back
     to text) and keep as one pair ("truncated") -- lossy, but keeps
     every ref represented rather than dropping it.

Downloads only the NLLB tokenizer files (a few MB: sentencepiece model +
config), not the ~2.5GB model itself -- that only happens in
src/baseline_bleu.py, which asks before downloading.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger

IN_PATH = PROJECT_ROOT / "data/processed/train.jsonl"
OUT_PATH = PROJECT_ROOT / "data/processed/train_ready.jsonl"
TOKENIZER_NAME = "facebook/nllb-200-distilled-600M"
MAX_TOKENS = 128

SENT_SPLIT_RE = re.compile(r"(?<=[.!?؟۔])\s+")


def split_sentences(text: str):
    parts = SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def main():
    logger = get_logger("prepare_for_training")
    from transformers import AutoTokenizer

    logger.info(f"Loading tokenizer {TOKENIZER_NAME} (tokenizer files only, not the model)...")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

    def n_tokens(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=False)["input_ids"])

    def truncate_to(text: str, max_tokens: int) -> str:
        ids = tokenizer(text, add_special_tokens=False)["input_ids"][:max_tokens]
        return tokenizer.decode(ids, skip_special_tokens=True)

    counts = defaultdict(int)
    out_rows = []

    with IN_PATH.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i % 20000 == 0:
                logger.info(f"...{i} input rows processed")
            p = json.loads(line)
            ar, tgt = p["ar"], p["tgt"]
            ar_n, tgt_n = n_tokens(ar), n_tokens(tgt)

            if ar_n <= MAX_TOKENS and tgt_n <= MAX_TOKENS:
                counts["as_is"] += 1
                row = dict(p)
                row["prep"] = "as_is"
                out_rows.append(row)
                continue

            ar_sents = split_sentences(ar)
            tgt_sents = split_sentences(tgt)
            if (
                len(ar_sents) > 1
                and len(ar_sents) == len(tgt_sents)
                and all(n_tokens(s) <= MAX_TOKENS for s in ar_sents)
                and all(n_tokens(s) <= MAX_TOKENS for s in tgt_sents)
            ):
                counts["split"] += 1
                for i, (a_s, t_s) in enumerate(zip(ar_sents, tgt_sents)):
                    row = dict(p)
                    row["id"] = f"{p['id']}:s{i}"
                    row["ar"] = a_s
                    row["tgt"] = t_s
                    row["prep"] = "split"
                    row["split_index"] = i
                    row["split_total"] = len(ar_sents)
                    out_rows.append(row)
                continue

            counts["truncated"] += 1
            row = dict(p)
            row["ar"] = truncate_to(ar, MAX_TOKENS)
            row["tgt"] = truncate_to(tgt, MAX_TOKENS)
            row["prep"] = "truncated"
            out_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_input = counts["as_is"] + counts["split"] + counts["truncated"]
    logger.info(
        f"Input pairs: {n_input} (as_is={counts['as_is']}, "
        f"split={counts['split']}, truncated={counts['truncated']})"
    )
    logger.info(f"Output rows: {len(out_rows)} (split pairs expand into multiple rows) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
