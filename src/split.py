"""
Split data/processed/cleaned.jsonl into train/valid/test by `ref` (not by
line), so every translation of the same verse/hadith stays in one split.
Writes both a combined file per split and one file per target language pair
for convenience.
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from common import PROJECT_ROOT, get_logger

IN_PATH = PROJECT_ROOT / "data/processed/cleaned.jsonl"
OUT_DIR = PROJECT_ROOT / "data/processed"
SEED = "arabic-mt-pipeline-v1"  # fixed, deterministic
SPLIT_WEIGHTS = [("train", 0.90), ("valid", 0.05), ("test", 0.05)]


def assign_split(ref: str) -> str:
    h = hashlib.sha256(f"{SEED}:{ref}".encode("utf-8")).hexdigest()
    bucket = int(h[:8], 16) / 0xFFFFFFFF  # deterministic float in [0, 1)
    acc = 0.0
    for name, weight in SPLIT_WEIGHTS:
        acc += weight
        if bucket < acc:
            return name
    return SPLIT_WEIGHTS[-1][0]


def main():
    logger = get_logger("split")
    pairs_by_ref = defaultdict(list)
    with IN_PATH.open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            pairs_by_ref[p["ref"]].append(p)

    split_of_ref = {ref: assign_split(ref) for ref in pairs_by_ref}

    combined = {"train": [], "valid": [], "test": []}
    per_pair = defaultdict(lambda: {"train": [], "valid": [], "test": []})

    for ref, items in pairs_by_ref.items():
        split = split_of_ref[ref]
        for p in items:
            combined[split].append(p)
            pair_key = f"ar_{p['tgt_lang']}"
            per_pair[pair_key][split].append(p)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for split in ("train", "valid", "test"):
        path = OUT_DIR / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for p in combined[split]:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        logger.info(f"{split}: {len(combined[split])} pairs -> {path}")

    for pair_key, splits in per_pair.items():
        for split in ("train", "valid", "test"):
            path = OUT_DIR / f"{split}.{pair_key}.jsonl"
            with path.open("w", encoding="utf-8") as f:
                for p in splits[split]:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
        logger.info(
            f"{pair_key}: train={len(splits['train'])} valid={len(splits['valid'])} test={len(splits['test'])}"
        )

    n_refs = len(pairs_by_ref)
    logger.info(f"{n_refs} distinct refs split into "
                f"train={sum(1 for s in split_of_ref.values() if s=='train')} "
                f"valid={sum(1 for s in split_of_ref.values() if s=='valid')} "
                f"test={sum(1 for s in split_of_ref.values() if s=='test')}")


if __name__ == "__main__":
    main()
