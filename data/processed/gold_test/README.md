# Gold test set (manual, not generated)

This folder is intentionally empty. It will hold 300-500 sentences drawn from
real sermons/lessons at the Two Holy Mosques, added manually (not scraped, not
machine-translated) once available.

Rules:
- These sentences must never be used for training or validation — they exist
  solely to measure real-world sermon-domain translation quality.
- Expected format: one JSONL file per target language pair, e.g.
  `gold_test.ar_en.jsonl`, following the same schema as
  `data/processed/{train,valid,test}.jsonl` (see project README), with
  `domain: "khutba"` and a `ref` that identifies the source recording/sermon
  and sentence index (e.g. `khutba:2024-03-15-jumuah:012`).
- Do not let anything in this folder leak into `src/split.py`'s train/valid/test
  splits — it is a separate, hand-curated set.
