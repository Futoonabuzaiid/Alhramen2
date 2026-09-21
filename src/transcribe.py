"""
Phase 2 scaffolding -- NOT RUN. Requires user approval before any audio is
downloaded or processed (see PLAN.md).

Draft-transcribes clips from audio_prep.py's manifest using Whisper Large V3
via faster-whisper, recording a per-segment confidence score. Output is
sorted lowest-confidence-first so review_tool.py surfaces the clips most
likely to need correction first.

Usage (once approved and dependencies installed):
    python src/transcribe.py --manifest data/processed/asr_clips/clips_manifest.jsonl \
        --out data/processed/asr_clips/transcripts.jsonl
"""
import argparse
import json
import math
from pathlib import Path

from common import PROJECT_ROOT, get_logger


def transcribe_clip(model, wav_path: str, start: float, end: float):
    """Returns (text, confidence) for one clip. Confidence is derived from
    faster-whisper's avg_logprob (converted to a 0-1-ish scale via exp)."""
    segments, _info = model.transcribe(
        wav_path, language="ar", clip_timestamps=[(start, end)], vad_filter=False,
    )
    texts, logprobs = [], []
    for seg in segments:
        texts.append(seg.text.strip())
        logprobs.append(seg.avg_logprob)
    text = " ".join(t for t in texts if t)
    confidence = math.exp(sum(logprobs) / len(logprobs)) if logprobs else 0.0
    return text, confidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--compute-type", default="float16")
    args = ap.parse_args()

    logger = get_logger("transcribe")
    from faster_whisper import WhisperModel  # noqa: local import, Phase 2 dependency only

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    results = []
    with open(args.manifest, encoding="utf-8") as f:
        for line in f:
            clip = json.loads(line)
            wav_path = str(PROJECT_ROOT / clip["audio_path"])
            text, confidence = transcribe_clip(model, wav_path, clip["start"], clip["end"])
            results.append({**clip, "text": text, "confidence": confidence})
            logger.info(f"{clip['clip_id']}: conf={confidence:.3f} text={text[:60]!r}")

    results.sort(key=lambda r: r["confidence"])  # lowest confidence first for review

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(results)} draft transcripts to {out_path}, sorted lowest-confidence first")


if __name__ == "__main__":
    main()
