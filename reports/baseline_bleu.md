# Baseline BLEU -- facebook/nllb-200-distilled-600M (zero-shot, no fine-tuning)

Evaluated on `data/processed/valid.ar_<lang>.jsonl`, max_examples=400 (domain-stratified sample, seed=20260101), batch_size=8.

| ar -> tgt | n | of full valid split | sacreBLEU | seconds |
|---|---:|---:|---:|---:|
| ar-en | 400 | 2255 | 6.44 | 3023 |
| ar-fr | 400 | 2041 | 5.54 | 3286 |
| ar-id | 400 | 2334 | 2.41 | 1618 |
| ar-ur | 400 | 2139 | 9.27 | 3817 |
| ar-tr | 400 | 2218 | 1.02 | 3467 |

## By domain

| ar -> tgt | domain | n | sacreBLEU |
|---|---|---:|---:|
| ar-en | hadith | 347 | 6.50 |
| ar-en | quran | 53 | 4.93 |
| ar-fr | hadith | 337 | 5.41 |
| ar-fr | quran | 63 | 7.91 |
| ar-id | hadith | 290 | 2.14 |
| ar-id | quran | 110 | 5.70 |
| ar-ur | hadith | 341 | 9.42 |
| ar-ur | quran | 59 | 6.11 |
| ar-tr | hadith | 288 | 0.88 |
| ar-tr | quran | 112 | 3.28 |