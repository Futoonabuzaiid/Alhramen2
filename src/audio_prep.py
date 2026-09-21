"""
Phase 2 scaffolding -- NOT RUN. Requires user approval before any audio is
downloaded or processed (see PLAN.md).

Converts source audio to 16kHz mono WAV via ffmpeg, then segments it into
5-30 second clips using Silero VAD, writing a manifest of clip boundaries.

Usage (once approved and dependencies installed):
    python src/audio_prep.py --input data/raw/<source>/audio/ --out data/processed/asr_clips/
"""
import argparse
import json
import subprocess
from pathlib import Path

from common import PROJECT_ROOT, get_logger

MIN_CLIP_SEC = 5.0
MAX_CLIP_SEC = 30.0


def to_16k_mono_wav(src_path: Path, dst_path: Path):
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src_path), "-ac", "1", "-ar", "16000", str(dst_path)],
        check=True, capture_output=True,
    )


def segment_with_silero_vad(wav_path: Path):
    """Returns a list of (start_sec, end_sec) speech segments, merged/split to
    respect MIN_CLIP_SEC/MAX_CLIP_SEC. Requires `silero-vad` + `torchaudio`."""
    import torch  # noqa: local import, Phase 2 dependency only

    model, utils = torch.hub.load("snakers4/silero-vad", "silero_vad", trust_repo=True)
    (get_speech_timestamps, _, read_audio, *_rest) = utils
    wav = read_audio(str(wav_path), sampling_rate=16000)
    raw_segments = get_speech_timestamps(wav, model, sampling_rate=16000, return_seconds=True)

    segments = []
    cur_start = None
    cur_end = None
    for seg in raw_segments:
        if cur_start is None:
            cur_start, cur_end = seg["start"], seg["end"]
            continue
        if seg["end"] - cur_start <= MAX_CLIP_SEC:
            cur_end = seg["end"]
        else:
            segments.append((cur_start, cur_end))
            cur_start, cur_end = seg["start"], seg["end"]
    if cur_start is not None:
        segments.append((cur_start, cur_end))

    return [(s, e) for s, e in segments if (e - s) >= MIN_CLIP_SEC]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="directory of source audio files")
    ap.add_argument("--out", required=True, help="output directory for prepped clips + manifest")
    args = ap.parse_args()

    logger = get_logger("audio_prep")
    in_dir = Path(args.input)
    out_dir = Path(args.out)
    manifest_path = out_dir / "clips_manifest.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("w", encoding="utf-8") as mf:
        for src in sorted(in_dir.glob("**/*")):
            if src.suffix.lower() not in {".wav", ".mp3", ".m4a", ".flac", ".ogg"}:
                continue
            wav_path = out_dir / "wav16k" / f"{src.stem}.wav"
            if not wav_path.exists():
                to_16k_mono_wav(src, wav_path)
                logger.info(f"converted {src} -> {wav_path}")
            segments = segment_with_silero_vad(wav_path)
            for i, (start, end) in enumerate(segments):
                mf.write(json.dumps({
                    "audio_path": str(wav_path.relative_to(PROJECT_ROOT)),
                    "clip_id": f"{src.stem}_{i:04d}",
                    "start": start, "end": end,
                }, ensure_ascii=False) + "\n")
            logger.info(f"{src.stem}: {len(segments)} clips")


if __name__ == "__main__":
    main()
