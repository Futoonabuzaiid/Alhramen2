.PHONY: download-quran download-hadith download-phase1 clean split report phase1 all

download-quran:
	python3 src/download_quran.py

download-hadith:
	python3 src/download_hadith.py

download-phase1: download-quran download-hadith

clean:
	python3 src/clean.py

split:
	python3 src/split.py

report:
	python3 src/report.py

# Phase 1: download -> clean -> split -> report
phase1: download-phase1 clean split report

all: phase1

# Phase 2 is scaffolding only -- these targets are NOT wired to run
# automatically. See PLAN.md; do not invoke without separate approval and
# the extra dependencies in requirements.txt.
phase2-audio-prep:
	python3 src/audio_prep.py --input data/raw/<source>/audio --out data/processed/asr_clips

phase2-transcribe:
	python3 src/transcribe.py --manifest data/processed/asr_clips/clips_manifest.jsonl --out data/processed/asr_clips/transcripts.jsonl

phase2-review:
	python3 src/review_tool.py --transcripts data/processed/asr_clips/transcripts.jsonl --out data/processed/asr_clips/reviewed.jsonl
