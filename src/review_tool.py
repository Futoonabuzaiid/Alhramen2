"""
Phase 2 scaffolding -- NOT RUN. Requires user approval before any audio is
downloaded or processed (see PLAN.md).

A minimal local Gradio UI to review draft ASR transcripts: play a clip, edit
the text, and save to a reviewed manifest. Clips are shown in the order
they appear in the input file (transcribe.py already sorts lowest-confidence
first, so reviewing top-to-bottom prioritizes the clips most likely wrong).

Usage (once approved and dependencies installed):
    python src/review_tool.py --transcripts data/processed/asr_clips/transcripts.jsonl \
        --out data/processed/asr_clips/reviewed.jsonl
"""
import argparse
import json
from pathlib import Path

from common import PROJECT_ROOT, get_logger


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def already_reviewed_ids(out_path: Path):
    if not out_path.exists():
        return set()
    return {r["clip_id"] for r in load_jsonl(out_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    logger = get_logger("review_tool")
    import gradio as gr  # noqa: local import, Phase 2 dependency only

    clips = load_jsonl(args.transcripts)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = already_reviewed_ids(out_path)
    queue = [c for c in clips if c["clip_id"] not in done]
    logger.info(f"{len(done)} already reviewed, {len(queue)} remaining")

    state = {"i": 0}

    def current():
        if state["i"] >= len(queue):
            return None, "", "All clips reviewed."
        c = queue[state["i"]]
        audio_path = str(PROJECT_ROOT / c["audio_path"])
        status = f"Clip {state['i'] + 1}/{len(queue)} | id={c['clip_id']} | confidence={c['confidence']:.3f}"
        return audio_path, c["text"], status

    def save_and_next(edited_text):
        if state["i"] < len(queue):
            c = queue[state["i"]]
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**c, "text": edited_text, "reviewed": True}, ensure_ascii=False) + "\n")
            state["i"] += 1
        return current()

    def skip():
        state["i"] += 1
        return current()

    with gr.Blocks() as demo:
        gr.Markdown("## ASR transcript review")
        status_box = gr.Textbox(label="Status", interactive=False)
        audio = gr.Audio(label="Clip", type="filepath")
        text = gr.Textbox(label="Transcript (edit as needed)", lines=3)
        with gr.Row():
            save_btn = gr.Button("Save & Next", variant="primary")
            skip_btn = gr.Button("Skip")

        demo.load(fn=current, outputs=[audio, text, status_box])
        save_btn.click(fn=save_and_next, inputs=[text], outputs=[audio, text, status_box])
        skip_btn.click(fn=skip, outputs=[audio, text, status_box])

    demo.launch()


if __name__ == "__main__":
    main()
