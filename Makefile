PYTHON ?= python3

.PHONY: download-quran download-hadith download-hadeethenc download-opus download-phase1 clean split report phase1 all

download-quran:
	$(PYTHON) src/download_quran.py

download-hadith:
	$(PYTHON) src/download_hadith.py

download-hadeethenc:
	$(PYTHON) src/download_hadeethenc.py

download-opus:
	$(PYTHON) src/download_opus.py

download-phase1: download-quran download-hadith download-hadeethenc download-opus

clean:
	$(PYTHON) src/clean.py

split:
	$(PYTHON) src/split.py

report:
	$(PYTHON) src/report.py

# Phase 1: download -> clean -> split -> report
phase1: download-phase1 clean split report

all: phase1

# Phase 2 is scaffolding only -- these targets are NOT wired to run
# automatically. See PLAN.md; do not invoke without separate approval and
# the extra dependencies in requirements.txt.
phase2-audio-prep:
	$(PYTHON) src/audio_prep.py --input data/raw/<source>/audio --out data/processed/asr_clips

phase2-transcribe:
	$(PYTHON) src/transcribe.py --manifest data/processed/asr_clips/clips_manifest.jsonl --out data/processed/asr_clips/transcripts.jsonl

phase2-review:
	$(PYTHON) src/review_tool.py --transcripts data/processed/asr_clips/transcripts.jsonl --out data/processed/asr_clips/reviewed.jsonl
