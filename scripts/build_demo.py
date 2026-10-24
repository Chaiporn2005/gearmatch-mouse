"""Build the edited, Thai-narrated walkthrough from actual UI captures.

Requires ffmpeg/ffprobe, Pillow and gTTS. The macOS Kanya voice is optional.
This does not automate a browser or fabricate app responses. UI stills were
captured via Computer Use; technical cards read the committed measured data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/demo"
CAPTURES = OUT / "captures"
WORK = ROOT / ".demo-build"
BG, FG, MUTED, ACCENT = "#12130f", "#e7e5de", "#9b9d91", "#9fc2b9"
FONT = Path("/System/Library/Fonts/Supplemental")


def run(args):
    subprocess.run([str(a) for a in args], check=True)


def font(size=24, bold=False):
    return ImageFont.truetype(str(FONT / ("Arial Bold.ttf" if bold else "Arial.ttf")), size)


def wrap(draw, text, xy, width, size=24, color=FG, leading=None, bold=False):
    x, y = xy
    words = text.split()
    line = ""
    f = font(size, bold)
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textlength(candidate, font=f) > width and line:
            draw.text((x, y), line, font=f, fill=color)
            y += leading or size * 1.4
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=f, fill=color)
        y += leading or size * 1.4
    return y


def card(title, subtitle):
    im = Image.new("RGB", (1280, 720), BG)
    d = ImageDraw.Draw(im)
    d.text((54, 42), title, font=font(38, True), fill=FG)
    wrap(d, subtitle, (54, 100), 1172, 23, MUTED)
    d.line((54, 153, 1226, 153), fill="#414437", width=2)
    return im, d


def technical_cards():
    im, d = card("A bounded, source-grounded agent", "Model: gemma-4-E4B-it / class proxy / native Chat Completions tools")
    boxes = [
        (54, 193, "1. QUESTION + FILTERS", "Budget / weight / connection / handedness"),
        (670, 193, "2. NATIVE TOOL REQUEST", "search_specs / filter_products"),
        (54, 338, "3. FILTER, THEN RANK", "BM25 + lexical TF-IDF + bilingual aliases / RRF k=60"),
        (670, 338, "4. VALIDATE THE ANSWER", "Schema + evidence IDs + original hard filters"),
    ]
    for x, y, heading, body in boxes:
        d.rounded_rectangle((x, y, x + 556, y + 120), 12, fill="#21251d", outline="#465344")
        d.text((x + 22, y + 18), heading, font=font(24, True), fill=ACCENT)
        wrap(d, body, (x + 22, y + 56), 512, 22)
    wrap(d, "Maximum 5 model turns / 4 tool calls per turn / repeated requests rejected", (54, 517), 1172, 25, ACCENT)
    wrap(d, "Structured output + retrieval + evaluation + agentic loop. Valid citation IDs do not establish sentence-level faithfulness.", (54, 586), 1172, 24, MUTED)
    im.save(CAPTURES / "10-architecture.png")

    measured = json.loads((ROOT / "evaluation/results.json").read_text())
    systems = measured["systems"]
    im, d = card("Held-out retrieval results", "30 curated cases / 20 dev + 10 held-out / 8 answerable test cases for Recall@3")
    rows = [("BM25 baseline", "bm25", "#767a6d"), ("Filtered BM25", "filtered_bm25", "#8eae9d"), ("Hybrid + aliases", "hybrid", "#cfdc85")]
    for i, (label, key, color) in enumerate(rows):
        y = 194 + i * 100
        value = systems[key]["test"]["recall_at_3"]
        d.text((54, y), label, font=font(25, True), fill=FG)
        d.rounded_rectangle((354, y, 354 + int(value * 705), y + 44), 5, fill=color)
        d.text((1086, y + 3), f"{value:.3f}", font=font(31, True), fill=color)
    d.text((54, 512), "Constraint violations: 11 baseline / 0 filtered / 0 hybrid", font=font(25), fill=ACCENT)
    wrap(d, "Retrieval measurement, not an LLM answer score. Author labels; no independent annotator or statistical-significance claim. Alias expansion and fusion are not separately ablated.", (54, 574), 1172, 24, MUTED)
    im.save(CAPTURES / "11-evaluation.png")

    before = json.loads((ROOT / "evaluation/live-before-fix.json").read_text())
    after = json.loads((ROOT / "evaluation/live-results.json").read_text())
    before_pass = sum(bool(x["passed"]) for x in before["cases"])
    after_pass = sum(bool(x["passed"]) for x in after["cases"])
    im, d = card("A real validation failure", "Historical traces retained: evaluation/live-before-fix.json and live-results.json")
    d.text((54, 193), 'Observed citation_ids: ["pebble", "pebbles"]', font=font(29, True), fill="#dfaa8b")
    d.text((54, 252), 'Expected ID: "logitech-pebble-2-m350s"', font=font(29, True), fill=ACCENT)
    wrap(d, "Two namespaces confused the model. Validation rejected the answer; repeated repair exhausted the turn limit.", (54, 323), 1172, 27)
    wrap(d, "Repair: one canonical citation namespace + separate routing and answer instructions.", (54, 424), 1172, 27, ACCENT)
    d.text((54, 535), f"Recorded live smoke suite: {before_pass}/{len(before['cases'])} before  ->  {after_pass}/{len(after['cases'])} after", font=font(31, True), fill=FG)
    wrap(d, "Three cases are a small smoke test, not broad reliability evidence. The planned no-match case is separate from this software failure.", (54, 600), 1172, 23, MUTED)
    im.save(CAPTURES / "12-failure.png")

    im, d = card("Inspect, reproduce, ask a new question", "GearMatch / Mouse Lab / capstone demonstration")
    d.text((54, 212), "github.com/Chaiporn2005/gearmatch-mouse", font=font(37, True), fill=ACCENT)
    for i, line in enumerate(["Source + manufacturer provenance + 30 labeled retrieval cases", "Reproducible evaluation scripts + recorded live traces", "Six-page report + Thai transcript + captions + demo video"]):
        d.text((54, 310 + i * 57), line, font=font(26), fill=FG)
    wrap(d, "Limits: 21 SKUs / USD reference prices / dated Cobra launch price / lexical vectors / no comfort or medical evaluation", (54, 528), 1172, 25, MUTED)
    d.text((54, 646), "Edited actual UI stills + measured-data cards / synthetic Thai narration", font=font(21), fill=MUTED)
    im.save(CAPTURES / "13-outro.png")


def duration(ffprobe, path):
    return float(subprocess.check_output([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], text=True).strip())


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", default=180, type=int)
    parser.add_argument("--voice", choices=["gtts", "say"], default="gtts")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--reuse-audio", action="store_true")
    parser.add_argument("--reuse-raw", action="store_true")
    args = parser.parse_args()
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    ffprobe = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    CAPTURES.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(exist_ok=True)
    chapters = json.loads((OUT / "narration.json").read_text())
    technical_cards()
    elapsed = 0.0
    for chapter in chapters:
        audio = WORK / (chapter["id"] + ".wav")
        text_path = WORK / (chapter["id"] + ".txt")
        text_path.write_text(chapter["narration"])
        if not args.reuse_audio or not audio.exists():
            raw = WORK / (chapter["id"] + (".mp3" if args.voice == "gtts" else ".aiff"))
            if args.reuse_raw and raw.exists():
                pass
            elif args.voice == "gtts":
                from gtts import gTTS
                # Only this public project narration is sent to Google's TTS.
                # No app keys, environment files or user data are transmitted.
                gTTS(chapter["narration"], lang="th", timeout=20).save(str(raw))
            else:
                run(["/usr/bin/say", "-v", "Kanya", "-r", args.rate, "-f", text_path, "-o", raw])
            run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-af", f"atempo={args.speed}", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", audio])
        chapter["duration"] = duration(ffprobe, audio)
        chapter["start"] = elapsed
        elapsed += chapter["duration"]
        print(f"{chapter['id']}: {chapter['duration']:.2f}s", flush=True)
    print(f"Total narration: {elapsed:.2f}s", flush=True)
    if args.audio_only:
        return
    if not 180 <= elapsed <= 360:
        raise ValueError("Narration must be 3-6 minutes; adjust --rate before rendering.")
    audio_list = WORK / "audio.ffconcat"
    audio_list.write_text("ffconcat version 1.0\n" + "".join(f"file '{(WORK / (c['id'] + '.wav')).as_posix()}'\n" for c in chapters))
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", audio_list, "-c:a", "pcm_s16le", WORK / "narration.wav"])
    frame_lines = ["ffconcat version 1.0"]
    subtitle_lines, transcript = [], ["# GearMatch demo: Thai narration\n", "Edited actual UI stills and measured-data cards; synthetic Kanya Thai narration.\n"]
    final_frame = None
    subtitle_index = 1
    for i, c in enumerate(chapters):
        transcript.extend([f"\n## {stamp(c['start'])[:-4]} — {c['title']}\n", c["narration"] + "\n"])
        sentences = [s.strip() for s in c["narration"].split(" ") if s.strip()]
        # Thai speech has no word delimiters; align phrase groups approximately.
        # These chapter-local caption timings are editorial, not ASR output.
        units = []
        current = ""
        for phrase in sentences:
            if len(current) + len(phrase) > 130 and current:
                units.append(current)
                current = phrase
            else:
                current = (current + " " + phrase).strip()
        if current:
            units.append(current)
        unit_start = c["start"]
        weight = sum(len(x) for x in units)
        for unit in units:
            end = unit_start + c["duration"] * len(unit) / weight
            subtitle_lines.extend([str(subtitle_index), f"{stamp(unit_start)} --> {stamp(end)}", unit, ""])
            subtitle_index += 1
            unit_start = end
        for j, image_name in enumerate(c["images"]):
            source = Image.open(CAPTURES / image_name).convert("RGB")
            # Keep all of the source view; no crop, fabricated overlay or answer edit.
            source.thumbnail((1152, 648), Image.Resampling.LANCZOS)
            frame = Image.new("RGB", (1280, 800), BG)
            frame.paste(source, ((1280 - source.width) // 2, 72 + (648 - source.height) // 2))
            d = ImageDraw.Draw(frame)
            d.text((40, 22), c["title"], font=font(23, True), fill=FG)
            d.text((1110, 25), f"{i + 1:02} / 08", font=font(19), fill=ACCENT)
            d.text((40, 750), c["caption"], font=font(18), fill=ACCENT)
            d.rectangle((0, 793, int(1280 * (i + 1) / len(chapters)), 799), fill=ACCENT)
            final_frame = WORK / f"frame-{i:02}-{j:02}.png"
            frame.save(final_frame)
            frame_lines.extend([f"file '{final_frame.as_posix()}'", f"duration {c['duration'] / len(c['images']):.6f}"])
    frame_lines.append(f"file '{final_frame.as_posix()}'")
    frame_list = WORK / "frames.ffconcat"
    frame_list.write_text("\n".join(frame_lines) + "\n")
    (OUT / "GearMatch-demo.th.srt").write_text("\n".join(subtitle_lines))
    (OUT / "NARRATION.th.md").write_text("\n".join(transcript).replace("synthetic Kanya Thai narration", "synthetic Thai narration"))
    chapter_meta = WORK / "chapters.ffmeta"
    chapter_meta.write_text(";FFMETADATA1\ntitle=GearMatch - Thai narrated demonstration\ncomment=Edited actual UI stills and measured-data cards; synthetic Thai narration.\n" + "".join(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(c['start'] * 1000)}\nEND={round((c['start'] + c['duration']) * 1000)}\ntitle={c['title']}\n" for c in chapters))
    video = OUT / "GearMatch-demo.mp4"
    run([ffmpeg, "-hide_banner", "-loglevel", "warning", "-y", "-f", "concat", "-safe", "0", "-i", frame_list, "-i", WORK / "narration.wav", "-i", OUT / "GearMatch-demo.th.srt", "-f", "ffmetadata", "-i", chapter_meta, "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map_metadata", "3", "-map_chapters", "3", "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "24", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "96k", "-metadata:s:a:0", "language=tha", "-c:s", "mov_text", "-metadata:s:s:0", "language=tha", "-metadata:s:s:0", "title=Thai (editorial timing)", "-disposition:s:0", "0", "-movflags", "+faststart", "-t", f"{elapsed:.6f}", "-shortest", video])
    Image.open(WORK / "frame-00-00.png").convert("RGB").save(OUT / "poster.jpg", quality=90)
    manifest = {"format": "Edited actual UI stills + measured-data cards; synthetic Thai narration", "voice": "Google Thai via gTTS" if args.voice == "gtts" else "macOS Kanya th_TH", "audio_speed": args.speed, "captions": "Thai; editorial phrase timing (not forced alignment)", "model": "gemma-4-E4B-it", "ui_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "duration_seconds": duration(ffprobe, video), "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "chapters": [{k: v for k, v in c.items() if k != "narration"} for c in chapters]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"video": str(video), "seconds": manifest["duration_seconds"], "bytes": video.stat().st_size}), flush=True)


if __name__ == "__main__":
    main()
