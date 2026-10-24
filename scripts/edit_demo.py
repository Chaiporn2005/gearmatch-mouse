"""Re-edit the narrated walkthrough into a faster, more readable cut.

Reuses the narration already in docs/demo/GearMatch-demo.mp4 and the committed
UI captures; nothing is re-recorded and no app response is changed. Technical
chapters are rebuilt as animated cards that show the same measured numbers.

Requires ffmpeg, Pillow, numpy and Google Chrome (used to typeset Thai text,
which Pillow cannot shape without libraqm).

    python scripts/edit_demo.py                 # full render
    python scripts/edit_demo.py --preview 12,95 # still frames only
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import os
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs/demo"
CAPTURES = DEMO / "captures"
WORK = ROOT / ".demo-build/edit"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H, FPS, SR = 1280, 720, 30, 48000
BG = (18, 19, 15)
TEAL, SOFT = (47, 156, 149), (92, 194, 186)

# ---------------------------------------------------------------- easing


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(p):
    return 1 - (1 - clamp(p)) ** 3


def ease_in_out(p):
    p = clamp(p)
    return 4 * p**3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


# ---------------------------------------------------------------- audio


def load_audio():
    raw = run(["ffmpeg", "-v", "error", "-i", DEMO / "GearMatch-demo.mp4", "-vn", "-ac", "1",
               "-ar", SR, "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def trim_silence(x, threshold_db=-42, min_gap=0.42, keep=0.12):
    """Shorten pauses longer than min_gap to 2*keep. Returns (audio, segments)."""
    win = SR // 100
    n = len(x) // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    silent = 20 * np.log10(rms) < threshold_db
    keep_mask = np.ones(n, bool)
    k = int(keep * 100)
    i = 0
    while i < n:
        if not silent[i]:
            i += 1
            continue
        j = i
        while j < n and silent[j]:
            j += 1
        if (j - i) / 100 >= min_gap:
            keep_mask[i + k : j - k] = False
        i = j
    segments, start = [], None
    for idx, kept in enumerate(np.append(keep_mask, False)):
        if kept and start is None:
            start = idx
        elif not kept and start is not None:
            segments.append((start * win, idx * win))
            start = None
    fade = np.linspace(0, 1, int(SR * 0.004), dtype=np.float32)
    parts, warp, cursor = [], [], 0
    for a, b in segments:
        part = x[a:b].copy()
        part[: len(fade)] *= fade
        part[-len(fade) :] *= fade[::-1]
        parts.append(part)
        warp.append((a / SR, b / SR, cursor / SR))
        cursor += b - a
    return np.concatenate(parts), warp


def warp_fn(warp):
    starts = [w[0] for w in warp]

    def f(t):
        i = bisect.bisect_right(starts, t) - 1
        if i < 0:
            return 0.0
        a, b, n0 = warp[i]
        return n0 + min(t, b) - a

    return f


def pad_music(seconds):
    """Soft sine pad, Am9 - Fmaj7 - Cmaj7 - G6, five seconds per chord."""
    chords = [[45, 48, 52, 55, 59], [41, 45, 48, 52], [48, 52, 55, 59], [43, 47, 50, 52]]
    out = np.zeros(int(seconds * SR) + SR * 8, np.float32)
    step, tail = 5.0, 2.0
    seg_t = np.arange(int((step + tail) * SR)) / SR
    env = np.minimum(1, seg_t / 1.6) * np.clip((step + tail - seg_t) / tail, 0, 1)
    env = (0.5 - 0.5 * np.cos(np.pi * env)).astype(np.float32)
    for c in range(int(seconds / step) + 1):
        notes = chords[c % len(chords)]
        voice = np.zeros_like(seg_t)
        for m in notes:
            f = 440 * 2 ** ((m - 69) / 12)
            voice += np.sin(2 * np.pi * f * seg_t) + np.sin(2 * np.pi * f * 1.003 * seg_t + 1.3)
            voice += 0.18 * np.sin(2 * np.pi * 2 * f * seg_t)
        root = 440 * 2 ** ((notes[0] - 12 - 69) / 12)
        voice += 0.8 * np.sin(2 * np.pi * root * seg_t)
        a = int(c * step * SR)
        out[a : a + len(seg_t)] += (voice * env).astype(np.float32)
    out = out[: int(seconds * SR)]
    t = np.arange(len(out)) / SR
    out *= (1 + 0.12 * np.sin(2 * np.pi * 0.17 * t)).astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def whoosh(rng, length=0.7):
    n = int(length * SR)
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    chunks = 10
    size = n // chunks
    freqs = np.fft.rfftfreq(size * 2, 1 / SR)
    for c in range(chunks):
        center = 400 * (8 ** math.sin(math.pi * c / (chunks - 1)))
        seg = noise[c * size : c * size + size * 2]
        if len(seg) < size * 2:
            seg = np.pad(seg, (0, size * 2 - len(seg)))
        spec = np.fft.rfft(seg * np.hanning(size * 2))
        spec *= np.exp(-((np.log2(freqs + 1) - np.log2(center)) ** 2) / 1.2)
        piece = np.fft.irfft(spec).astype(np.float32)
        a = c * size
        b = min(n, a + size * 2)
        out[a:b] += piece[: b - a]
    t = np.linspace(0, 1, n)
    env = np.where(t < 0.62, (t / 0.62) ** 2, ((1 - t) / 0.38) ** 1.5)
    out *= env.astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- typesetting via Chrome

CSS = """
:root{--fg:#e4dfda;--dim:#e4dfda99;--faint:#e4dfda61;--line:#e4dfda26;--soft:#5cc2ba;--warn:#ec9677}
*{box-sizing:border-box}html,body{margin:0;background:transparent}
body{font-family:"Hanken Grotesk","Noto Sans Thai",sans-serif;color:var(--fg);-webkit-font-smoothing:antialiased}
.slot{position:relative;overflow:hidden}.a{position:absolute}
.th{font-family:"Noto Sans Thai","Hanken Grotesk",sans-serif}
.mono{font-family:"Geist Mono",ui-monospace,monospace}
.display{font-family:"Anybody",sans-serif;font-weight:800;font-variation-settings:"wdth" 75;line-height:.95}
.eyebrow{left:64px;top:52px;font:500 14px "Geist Mono";letter-spacing:.1em;color:var(--soft)}
.title{left:64px;top:76px;font-size:56px}
.chip{display:inline-block;border:1px solid var(--line);border-radius:5px;padding:5px 10px;margin:0 6px 8px 0;
  font:500 14px "Geist Mono";background:#e4dfda0d;white-space:nowrap}
.card{background:#1b1c17;border:1px solid var(--line);border-radius:10px;padding:20px}
.bg{left:0;top:0;width:1280px;height:720px;background:#12130f}
"""
FONTS = ("https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,100..900"
         "&family=Geist+Mono:wght@400..700&family=Hanken+Grotesk:wght@400..800"
         "&family=Noto+Sans+Thai:wght@400..700&display=block")


class Sprites:
    def __init__(self):
        self.specs, self.images = {}, {}

    def add(self, name, w, h, html):
        self.specs[name] = (w, h, html)
        return name

    def render(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        pages, page, height = [], [], 0
        for name, (w, h, _) in self.specs.items():
            if height + h > 7200 and page:
                pages.append(page)
                page, height = [], 0
            page.append(name)
            height += h
        if page:
            pages.append(page)
        for n, names in enumerate(pages):
            body = "".join(
                f'<div class="slot" style="width:{self.specs[k][0]}px;height:{self.specs[k][1]}px">{self.specs[k][2]}</div>'
                for k in names)
            html = folder / f"page-{n}.html"
            html.write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}">'
                            f"<style>{CSS}</style><body>{body}</body>", encoding="utf-8")
            total = sum(self.specs[k][1] for k in names)
            png = folder / f"page-{n}.png"
            run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                 "--default-background-color=00000000", "--virtual-time-budget=20000",
                 f"--window-size=1280,{total}", f"--screenshot={png}", html.as_uri()],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sheet = Image.open(png).convert("RGBA")
            y = 0
            for k in names:
                w, h, _ = self.specs[k]
                crop = sheet.crop((0, y, w, y + h))
                box = crop.getbbox() or (0, 0, 1, 1)
                self.images[k] = (crop.crop(box), box[:2])
                y += h

    def __getitem__(self, name):
        return self.images[name]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- scenes


class Scene:
    """Animated card: sprite layers that rise into place, plus optional drawing."""

    def __init__(self, name, sprites, layers, draw=None, length=40.0):
        self.name, self.layers, self.draw, self.length = name, [], draw, length
        for i, (t, html) in enumerate(layers):
            self.layers.append((t, sprites.add(f"{name}-{i}", W, H, html)))
        self.sprites = sprites

    def render(self, t):
        canvas = Image.new("RGBA", (W, H), BG + (255,))
        for appear, key in self.layers:
            if t < appear:
                continue
            img, (x, y) = self.sprites[key]
            p = ease_out((t - appear) / 0.5)
            if p >= 1:
                canvas.alpha_composite(img, (x, y))
            else:
                faded = img.copy()
                faded.putalpha(img.getchannel("A").point(lambda v: int(v * p)))
                canvas.alpha_composite(faded, (x, int(y + 18 * (1 - p))))
        if self.draw:
            self.draw(canvas, t)
        z = 1 + 0.035 * clamp(t / self.length)
        return camera(canvas.convert("RGB"), (640, 340, z))


def aa_round_rect(size, radius, fill=None, outline=None, width=2, scale=3):
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius * scale,
                                          fill=fill, outline=outline, width=width * scale)
    return big.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- camera / stills


def camera(img, state):
    cx, cy, z = state
    cw, ch = W / z, H / z
    cx = clamp(cx, cw / 2, img.width - cw / 2)
    cy = clamp(cy, ch / 2, img.height - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.transform((W, H), Image.EXTENT, box, Image.BICUBIC)


def to_screen(rect, state, src_size=(W, H + 160)):
    cx, cy, z = state
    cw, ch = W / z, H / z
    cx = clamp(cx, cw / 2, src_size[0] - cw / 2)
    cy = clamp(cy, ch / 2, src_size[1] - ch / 2)
    x0, y0 = cx - cw / 2, cy - ch / 2
    return [((rect[0] - x0) * z) - 8, ((rect[1] - y0) * z) - 6, ((rect[2] - x0) * z) + 8, ((rect[3] - y0) * z) + 6]


def spotlight(frame, rect, alpha):
    if alpha <= 0.01:
        return frame
    mask = Image.new("L", (W, H), int(125 * alpha))
    ImageDraw.Draw(mask).rounded_rectangle(rect, 10, fill=0)
    frame = Image.composite(Image.new("RGB", (W, H), (6, 7, 5)), frame, mask)
    ring = aa_round_rect((rect[2] - rect[0], rect[3] - rect[1]), 10, outline=TEAL + (int(255 * alpha),), width=2)
    frame = frame.convert("RGBA")
    frame.alpha_composite(ring, (int(rect[0]), int(rect[1])))
    return frame.convert("RGB")


class Beat:
    def __init__(self, t, src, cx=640, cy=360, z=1.0, hl=None):
        self.t, self.src, self.target, self.hl = t, src, (cx, cy, z), hl
        self.start = None


def lerp_state(a, b, p):
    return (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p,
            math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * p))


def beat_state(beat, t, drift=0.007):
    move = 1.1 if beat.start != beat.target else 0.9
    s = lerp_state(beat.start, beat.target, ease_in_out((t - beat.t) / move))
    return (s[0], s[1], s[2] * (1 + drift * max(0, t - beat.t)))


def link_beats(beats):
    for i, b in enumerate(beats):
        prev = beats[i - 1] if i else None
        if prev is not None and prev.src is b.src and not isinstance(b.src, Scene):
            b.start = beat_state(prev, b.t)
        else:
            b.start = (b.target[0], b.target[1], b.target[2] * 1.05)


# ---------------------------------------------------------------- build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEMO / "GearMatch-demo-edit.mp4"))
    parser.add_argument("--preview", help="comma-separated seconds; writes stills instead of a video")
    parser.add_argument("--no-music", action="store_true")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((DEMO / "manifest.json").read_text())
    chapters = manifest["chapters"]
    audio = load_audio()

    # Narration per chapter, with long pauses shortened.
    hook = 4.9
    cursor = hook
    for i, c in enumerate(chapters):
        a = int(c["start"] * SR)
        b = int((c["start"] + c["duration"]) * SR)
        c["audio"], warp = trim_silence(audio[a:b])
        c["warp"] = warp_fn(warp)
        c["pre"] = 0.3 if i == 0 else 0.9
        c["g0"] = cursor
        c["len"] = c["pre"] + len(c["audio"]) / SR + (3.4 if i == len(chapters) - 1 else 0.35)
        cursor += c["len"]
    total = cursor
    before = sum(c["duration"] for c in chapters)
    after = sum(len(c["audio"]) / SR for c in chapters)
    print(f"narration {before:.1f}s -> {after:.1f}s; video {total:.1f}s; chapters at "
          + ", ".join(f"{c['g0']:.1f}" for c in chapters))

    def tm(ci, t):
        """Original chapter-local narration time -> chapter-local video time."""
        return chapters[ci]["pre"] + chapters[ci]["warp"](t)

    sp = Sprites()

    # ---- animated technical chapters (same numbers as the original cards)
    def head(eyebrow, title):
        return [f'<div class="a eyebrow">{eyebrow}</div><div class="a title display">{title}</div>']

    steps = [("Question + filters", "งบ · น้ำหนัก · การเชื่อมต่อ · มือที่ถนัด"),
             ("Native tool request", "โมเดลต้องขอใช้เครื่องมือก่อนตอบ"),
             ("Filter, then rank", "กรองเงื่อนไขบังคับก่อน แล้วจึงจัดอันดับ"),
             ("Validate the answer", "ตรวจสคีมา รหัสสินค้า และหลักฐาน")]

    def step_html(i):
        x = 64 + i * 290
        arrow = f'<div class="a mono" style="left:{x - 24}px;top:270px;color:var(--faint);font-size:18px">→</div>' if i else ""
        return (arrow + f'<div class="a card" style="left:{x}px;top:200px;width:260px;height:176px">'
                f'<div class="mono" style="color:var(--soft);font-size:14px">0{i + 1}</div>'
                f'<div style="font-size:23px;font-weight:600;margin-top:10px;line-height:1.15">{steps[i][0]}</div>'
                f'<div class="th" style="font-size:15px;color:var(--dim);margin-top:8px;line-height:1.5">{steps[i][1]}</div></div>')

    def chips(x, top, items, width=260):
        return (f'<div class="a" style="left:{x}px;top:{top}px;width:{width}px">'
                + "".join(f'<span class="chip">{esc(s)}</span>' for s in items) + "</div>")

    ci = 4
    step_t = [tm(ci, s) for s in (0.3, 4.0, 10.8, 28.5)]
    loop_t = [tm(ci, s) for s in (35.5, 38.0)]

    def draw_loop(canvas, t):
        stops = [(step_t[0], 0), (step_t[1], 1), (step_t[2], 2), (step_t[3], 3), (loop_t[0], 1), (loop_t[1], 3)]
        if t < stops[0][0]:
            return
        pos = stops[0][1]
        for tb, b in stops[1:]:
            if t >= tb:
                pos += (b - pos) * ease_in_out((t - tb) / 0.6)
        alpha = ease_out((t - stops[0][0]) / 0.4)
        ring = aa_round_rect((268, 184), 12, outline=TEAL + (int(255 * alpha),), width=2)
        canvas.alpha_composite(ring, (int(60 + pos * 290), 196))

    loop_svg = ('<svg class="a" style="left:0;top:0" width="1280" height="720"><path d="M1064 496 V514 H484 V500" '
                'fill="none" stroke="#5cc2ba" stroke-width="2"/><path d="M477 504 L484 492 L491 504" fill="none" '
                'stroke="#5cc2ba" stroke-width="2"/></svg>')
    architecture = Scene("architecture", sp, [
        (tm(ci, 0.0), head("04 · HOW IT WORKS", "A bounded, source-grounded agent")[0]),
        (tm(ci, 0.2), '<div class="a mono" style="left:64px;top:142px;color:var(--dim);font-size:15px">'
                      'gemma-4-E4B-it · class proxy · native tool calls</div>'),
        *[(step_t[i], step_html(i)) for i in range(4)],
        (tm(ci, 7.2), chips(354, 392, ["search_specs", "filter_products"])),
        (tm(ci, 15.0), chips(644, 392, ["BM25", "TF-IDF", "RRF k=60"])),
        (tm(ci, 23.0), '<div class="a th" style="left:644px;top:432px;width:260px;font-size:13px;color:var(--dim);'
                       'line-height:1.45">TF-IDF ในเครื่อง ไม่ใช่ semantic embedding</div>'),
        (tm(ci, 32.0), chips(934, 392, ["schema", "product IDs", "evidence", "original filters"])),
        (loop_t[0], loop_svg),
        (loop_t[0] + 0.2, chips(64, 528, ["≤ 5 model turns", "≤ 4 tool calls / turn"], 560)),
        (tm(ci, 38.5), chips(484, 528, ["unknown tools rejected", "repeated requests rejected"], 700)),
        (tm(ci, 41.6), '<div class="a" style="left:64px;top:578px;font-size:15px;color:var(--faint)">'
                       'Valid citation IDs do not prove every sentence is faithful.</div>'),
    ], draw_loop, chapters[ci]["len"])

    ci = 5
    bars = [("BM25 baseline", "lexical only", 0.438, (138, 140, 128), 13.5),
            ("Filtered BM25", "+ hard filters first", 0.500, (73, 128, 122), 17.5),
            ("Hybrid + aliases", "BM25 + TF-IDF + aliases → RRF", 0.969, SOFT, 20.6)]
    count_frames = 27
    for b, (_, _, value, _, _) in enumerate(bars):
        for k in range(count_frames):
            v = value * ease_out(k / (count_frames - 1))
            colour = "var(--soft)" if b == 2 else "var(--fg)"
            sp.add(f"count-{b}-{k}", 220, 64, f'<div class="a display" style="left:0;top:4px;font-size:46px;'
                   f'color:{colour};font-variation-settings:\'wdth\' 90">{v:.3f}</div>')
    bar_t = [tm(ci, b[4]) for b in bars]

    def draw_bars(canvas, t):
        for i, (_, _, value, colour, _) in enumerate(bars):
            if t < bar_t[i]:
                continue
            p = ease_out((t - bar_t[i]) / 0.9)
            width = max(8, 680 * value * p)
            canvas.alpha_composite(aa_round_rect((width, 34), 6, fill=colour + (255,)), (330, 238 + 85 * i))
            img, (x, y) = sp[f"count-{i}-{round(p * (count_frames - 1))}"]
            canvas.alpha_composite(img, (1040 + x, 226 + 85 * i + y))

    caveats = [(25.5, "Retrieval measurement, not an LLM answer score"),
               (32.2, "Author-made labels; no independent annotator"),
               (36.5, "Alias expansion and fusion are not separately ablated"),
               (40.8, "No statistical-significance claim")]
    evaluation = Scene("evaluation", sp, [
        (tm(ci, 0.0), head("05 · MEASURED RETRIEVAL", "Held-out retrieval results")[0]),
        (tm(ci, 1.0), chips(64, 160, ["30 curated cases"], 400)),
        (tm(ci, 4.0), chips(240, 160, ["20 dev"], 400)),
        (tm(ci, 5.5), chips(330, 160, ["10 held-out"], 400)),
        (tm(ci, 7.5), chips(458, 160, ["8 answerable + 2 no-match"], 500)),
        (tm(ci, 10.5), '<div class="a mono" style="left:330px;top:212px;font-size:13px;color:var(--faint);'
                       'letter-spacing:.08em">RECALL@3 · HELD-OUT</div>'),
        *[(bar_t[i] - 0.3, f'<div class="a" style="left:64px;top:{232 + 85 * i}px;width:250px">'
                           f'<div style="font-size:22px;font-weight:600">{name}</div>'
                           f'<div class="mono" style="font-size:13px;color:var(--faint);margin-top:2px">{esc(sub)}</div></div>'
                           f'<div class="a" style="left:330px;top:{238 + 85 * i}px;width:680px;height:34px;'
                           f'border-radius:6px;background:#e4dfda12"></div>')
          for i, (name, sub, _, _, _) in enumerate(bars)],
        (tm(ci, 24.5), '<div class="a mono" style="left:64px;top:478px;font-size:15px;color:var(--dim)">'
                       'Constraint violations — baseline 11 · filtered 0 · hybrid 0</div>'),
        *[(tm(ci, s), f'<div class="a" style="left:64px;top:{512 + 25 * i}px;font-size:16px;color:var(--faint)">'
                      f'— {text}</div>') for i, (s, text) in enumerate(caveats)],
    ], draw_bars, chapters[ci]["len"])

    ci = 6
    pip_t = [tm(ci, 13.0 + 0.75 * k) for k in range(5)]
    failure = Scene("failure", sp, [
        (tm(ci, 0.0), head("06 · A REAL FAILURE", "Validation caught a real mistake")[0]),
        (tm(ci, 3.0), '<div class="a mono" style="left:64px;top:172px;font-size:13px;color:var(--faint);'
                      'letter-spacing:.08em">BEFORE THE FIX · LIVE RUN</div><div class="a card" '
                      'style="left:64px;top:198px;width:560px;height:150px"></div>'),
        (tm(ci, 6.5), '<div class="a mono" style="left:88px;top:226px;font-size:17px;color:var(--warn)">'
                      '"citation_ids": ["pebble", "pebbles"]</div>'),
        (tm(ci, 10.8), '<div class="a mono" style="left:88px;top:278px;font-size:17px;color:var(--soft)">'
                       'expected → "logitech-pebble-2-m350s"</div>'),
        (tm(ci, 12.0), '<div class="a mono" style="left:474px;top:214px;transform:rotate(-8deg);border:2px solid '
                       'var(--warn);color:var(--warn);font-weight:700;font-size:16px;letter-spacing:.12em;'
                       'padding:4px 10px;border-radius:4px">REJECTED</div>'),
        (pip_t[0] - 0.3, '<div class="a mono" style="left:64px;top:374px;font-size:13px;color:var(--faint);'
                         'letter-spacing:.08em">REPAIR TURNS</div>'
                         + "".join(f'<div class="a" style="left:{64 + 44 * k}px;top:400px;width:32px;height:32px;'
                                   f'border:1px solid var(--line);border-radius:5px"></div>' for k in range(5))),
        *[(pip_t[k], f'<div class="a" style="left:{64 + 44 * k}px;top:400px;width:32px;height:32px;'
                     f'background:var(--warn);border-radius:5px"></div>') for k in range(5)],
        (tm(ci, 16.8), '<div class="a mono" style="left:296px;top:406px;font-size:15px;color:var(--warn)">'
                       'turn limit exhausted</div>'),
        (tm(ci, 18.0), '<div class="a mono" style="left:680px;top:172px;font-size:13px;color:var(--soft);'
                       'letter-spacing:.08em">THE FIX</div>'),
        (tm(ci, 19.5), '<div class="a card" style="left:680px;top:198px;width:536px;height:72px;padding:14px 20px">'
                       '<div style="font-size:20px;font-weight:600">One canonical citation namespace</div>'
                       '<div class="th" style="font-size:14px;color:var(--dim)">เครื่องมือแสดงรหัสอ้างอิงมาตรฐานเพียงชุดเดียว</div></div>'),
        (tm(ci, 22.5), '<div class="a card" style="left:680px;top:280px;width:536px;height:72px;padding:14px 20px">'
                       '<div style="font-size:20px;font-weight:600">Routing ≠ answering instructions</div>'
                       '<div class="th" style="font-size:14px;color:var(--dim)">แยกคำสั่งเลือกเครื่องมือ ออกจากคำสั่งสร้างคำตอบ</div></div>'),
        (tm(ci, 27.0), '<div class="a mono" style="left:680px;top:380px;font-size:13px;color:var(--faint);'
                       'letter-spacing:.08em">RECORDED LIVE SMOKE SUITE</div>'),
        (tm(ci, 27.6), '<div class="a display" style="left:680px;top:404px;font-size:68px">1/3 → '
                       '<span style="color:var(--soft)">3/3</span></div>'),
        (tm(ci, 30.5), '<div class="a" style="left:680px;top:482px;width:536px;font-size:16px;color:var(--dim)">'
                       'Three cases: a small smoke test, not broad reliability evidence.</div>'),
        (tm(ci, 36.2), '<div class="a mono" style="left:680px;top:516px;font-size:14px;color:var(--faint)">'
                       'evaluation/live-before-fix.json · kept in the repo</div>'),
    ], None, chapters[ci]["len"])

    ci = 7
    checks = ["Source code", "21-SKU catalog + manufacturer sources", "30 labeled retrieval cases",
              "Evaluation scripts + results", "Recorded live traces", "Six-page report"]
    outro = Scene("outro", sp, [
        (tm(ci, 22.5), head("07 · INSPECT &amp; REPRODUCE", "Everything is in the repo")[0]),
        (tm(ci, 22.8), '<div class="a mono" style="left:64px;top:160px;font-size:30px;color:var(--soft)">'
                       'github.com/Chaiporn2005/gearmatch-mouse</div>'),
        *[(tm(ci, 23.2 + 0.6 * k), f'<div class="a" style="left:{64 + 576 * (k % 2)}px;top:{232 + 46 * (k // 2)}px;'
                                   f'font-size:20px"><span style="color:var(--soft)">✓</span>&nbsp; {esc(s)}</div>')
          for k, s in enumerate(checks)],
        (tm(ci, 29.8), '<div class="a th" style="left:64px;top:398px;font-size:24px">'
                       'ผู้ตรวจตั้งค่า class proxy ในเครื่อง แล้วลองคำถามใหม่ได้</div>'),
        (tm(ci, 33.5), chips(64, 452, ["API key is never embedded in the page or uploaded to the repo"], 900)),
    ], None, chapters[ci]["len"])

    def end_html(t0):
        return [
            (t0, '<div class="a display" style="left:0;width:1280px;top:190px;text-align:center;font-size:150px;'
                 'font-variation-settings:\'wdth\' 110">GearMatch</div>'),
            (t0 + 0.35, '<div class="a th" style="left:0;width:1280px;top:368px;text-align:center;font-size:28px;'
                        'color:var(--dim)">ช่วยจำกัดตัวเลือก พร้อมบอกหลักฐานและความไม่แน่นอน</div>'),
            (t0 + 0.7, '<div class="a mono" style="left:0;width:1280px;top:430px;text-align:center;font-size:17px;'
                       'color:var(--soft)">github.com/Chaiporn2005/gearmatch-mouse</div>'),
            (t0 + 1.1, '<div class="a" style="left:0;width:1280px;top:560px;text-align:center;font-size:13px;'
                       'color:var(--faint)">Edited actual UI stills · cards rebuilt from measured repository data · '
                       'synthetic Thai narration (gTTS)</div>'),
        ]

    ending = Scene("ending", sp, end_html(tm(7, 40.3)), None, chapters[7]["len"])
    hook_card = Scene("hook", sp, [
        (0, '<div class="a display" style="left:0;width:1280px;top:205px;text-align:center;font-size:150px;'
            'font-variation-settings:\'wdth\' 110">GearMatch</div>'),
        (0.15, '<div class="a th" style="left:0;width:1280px;top:385px;text-align:center;font-size:30px">'
               'หาเมาส์ที่ใช่ จากสเปกที่ตรวจสอบได้</div>'),
        (0.3, '<div class="a mono" style="left:0;width:1280px;top:448px;text-align:center;font-size:15px;'
              'color:var(--faint);letter-spacing:.08em">21 MICE · MANUFACTURER SOURCES · THAI + ENGLISH</div>'),
    ], None, 1.5)

    # ---- shot lists (image coordinates from the 1280x720 captures)
    def B(ci, t, src, cx=640, cy=360, z=1.0, hl=None):
        return Beat(tm(ci, t), src, cx, cy, z, hl)

    # Extra background below each capture lets the camera lift bottom-edge
    # details clear of the captions.
    s = {}
    for f in CAPTURES.glob("[0-9][0-9]-*.*"):
        padded = Image.new("RGB", (W, H + 160), BG)
        padded.paste(Image.open(f).convert("RGB"))
        s[f.stem] = padded
    beats = [
        [B(0, 0.0, s["01-hero"], 640, 360, 1.0), B(0, 3.6, s["01-hero"], 995, 560, 1.85, (765, 485, 1230, 580)),
         B(0, 10.7, s["02-catalog"], 640, 360, 1.05), B(0, 15.0, s["02-catalog"], 1060, 140, 2.2, (1132, 86, 1227, 118)),
         B(0, 18.5, s["02-catalog"], 820, 470, 1.55), B(0, 21.5, s["02-catalog"], 543, 312, 2.4),
         B(0, 25.5, s["02-catalog"], 640, 360, 1.08), B(0, 29.8, s["01-hero"], 640, 230, 1.35)],
        [B(1, 0.0, s["03-success-input"], 215, 190, 2.3, (77, 135, 350, 243)),
         B(1, 3.4, s["03-success-input"], 215, 505, 2.3, (74, 474, 352, 536)),
         B(1, 5.8, s["03-success-input"], 215, 625, 2.0, (74, 598, 352, 716)),
         B(1, 8.6, s["03-success-input"], 545, 400, 1.55, (413, 209, 674, 575)),
         B(1, 11.2, s["04-success-answer"], 820, 360, 1.15),
         B(1, 13.6, s["04-success-answer"], 820, 290, 1.5, (432, 233, 1212, 284)),
         B(1, 17.6, s["04-success-answer"], 700, 340, 2.2, (430, 302, 686, 331)),
         B(1, 21.6, s["04-success-answer"], 700, 380, 2.2, (430, 371, 668, 395)),
         B(1, 27.8, s["04-success-answer"], 700, 450, 2.2, (430, 464, 654, 488)),
         B(1, 31.2, s["04-success-answer"], 820, 370, 1.2, (413, 209, 1227, 509))],
        [B(2, 0.0, s["05-evidence"], 640, 360, 1.0), B(2, 1.3, s["05-evidence"], 785, 165, 1.75, (546, 88, 1000, 180)),
         B(2, 4.8, s["05-evidence"], 785, 515, 1.9, (546, 476, 1022, 556)),
         B(2, 8.3, s["05-evidence"], 785, 305, 2.2, (546, 281, 1016, 333)),
         B(2, 14.4, s["06-compare"], 640, 360, 1.0), B(2, 16.6, s["06-compare"], 440, 470, 1.4),
         B(2, 19.8, s["07-compare-specs"], 640, 236, 1.95, (472, 222, 810, 252)),
         B(2, 26.0, s["07-compare-specs"], 440, 300, 1.35),
         B(2, 30.5, s["07-compare-specs"], 245, 437, 2.3, (72, 421, 412, 453))],
        [B(3, 0.0, s["08-negative-answer"], 215, 178, 2.3, (77, 135, 350, 243)),
         B(3, 3.8, s["08-negative-answer"], 215, 600, 1.75, (74, 474, 352, 716)),
         B(3, 8.4, s["08-negative-answer"], 820, 290, 1.6, (432, 258, 1216, 310)),
         B(3, 12.6, s["08-negative-answer"], 1110, 110, 2.6, (1139, 82, 1227, 116)),
         B(3, 15.0, s["08-negative-answer"], 820, 560, 1.9, (690, 522, 950, 596)),
         B(3, 19.2, s["08-negative-answer"], 213, 650, 2.4, (76, 677, 209, 717)),
         B(3, 27.6, s["08-negative-answer"], 640, 360, 1.05)],
        [Beat(0, architecture)],
        [Beat(0, evaluation)],
        [Beat(0, failure)],
        [B(7, 0.0, s["09-about"], 640, 300, 1.15), B(7, 1.2, s["09-about"], 330, 455, 1.95, (52, 370, 605, 508)),
         B(7, 5.5, s["09-about"], 950, 455, 1.95, (674, 370, 1228, 508)), B(7, 16.0, s["09-about"], 640, 520, 1.2),
         Beat(tm(7, 22.5), outro), Beat(tm(7, 40.3), ending)],
    ]
    for c, bs in zip(chapters, beats):
        link_beats(bs)
        c["beats"] = bs

    # Opening montage: hard cuts, no narration.
    hook_shots = [
        (0.0, 0.9, s["01-hero"], (640, 250, 1.0), (640, 210, 1.3), None),
        (0.9, 1.7, s["04-success-answer"], (780, 320, 1.75), (760, 320, 1.85), (430, 302, 686, 331)),
        (1.7, 2.5, s["07-compare-specs"], (640, 236, 2.1), (600, 236, 2.2), (472, 222, 810, 252)),
        (2.5, 3.4, evaluation, None, None, None),
        (3.4, hook, hook_card, None, None, None),
    ]

    # ---- titles, labels, captions
    thai_titles = ["", "คำตอบสดที่อ้างอิงข้อมูลจริง", "เปิดหลักฐาน แล้วเทียบสเปก", "ไม่พบ ก็เป็นคำตอบที่ถูกต้อง",
                   "ลูปเครื่องมือที่มีขอบเขต", "ผลการค้นคืนที่วัดได้", "ข้อผิดพลาดจริง และวิธีแก้", "ข้อจำกัด และวิธีตรวจซ้ำ"]
    for i, c in enumerate(chapters):
        num, _, name = c["title"].partition(" / ")
        if i:
            sp.add(f"card-{i}", W, H,
                   '<div class="a bg"></div>'
                   f'<div class="a display" style="left:760px;top:120px;font-size:420px;color:#e4dfda12">{num}</div>'
                   '<div class="a" style="left:64px;top:0;height:720px;width:900px;display:flex;'
                   'flex-direction:column;justify-content:center;gap:18px">'
                   f'<div class="mono" style="font-size:15px;color:var(--soft);letter-spacing:.1em">{num} / 07</div>'
                   f'<div class="display" style="font-size:76px">{esc(name)}</div>'
                   f'<div class="th" style="font-size:28px;color:var(--dim)">{thai_titles[i]}</div></div>')
        label = "GEARMATCH · MOUSE LAB" if not i else f"{num} · {name.upper()}"
        sp.add(f"label-{i}", 700, 48, f'<div class="a mono" style="left:0;top:0;font-size:12px;letter-spacing:.08em;'
               f'padding:7px 11px;border-radius:6px;background:#12130fd9;border:1px solid var(--line)">{esc(label)}</div>')

    cues = []
    srt = (DEMO / "GearMatch-demo.th.srt").read_text(encoding="utf-8").strip().split("\n\n")
    stamp = lambda s: sum(float(x) * m for x, m in zip(re.split("[:,]", s), (3600, 60, 1, 0.001)))  # noqa: E731
    for block in srt:
        lines = block.splitlines()
        a, b = (stamp(x.strip()) for x in lines[1].split("-->"))
        text = " ".join(lines[2:])
        ci = max(i for i, c in enumerate(chapters) if c["start"] <= a + 0.01)
        words, phrases, cur = text.split(), [], ""
        for w in words:
            cand = (cur + " " + w).strip()
            if len(cand) > 40 and cur:
                phrases.append(cur)
                cur = w
            else:
                cur = cand
        phrases.append(cur)
        weights = [len(p) + 4 for p in phrases]
        t = a
        for p, wgt in zip(phrases, weights):
            span = (b - a) * wgt / sum(weights)
            g = lambda x: chapters[ci]["g0"] + tm(ci, x - chapters[ci]["start"])  # noqa: E731
            cues.append((g(t), g(t + span), p))
            t += span
    for k, (_, _, text) in enumerate(cues):
        sp.add(f"cap-{k}", W, 90, f'<div class="a th" style="left:0;width:1280px;top:10px;text-align:center">'
               f'<span style="display:inline-block;max-width:1100px;font-size:30px;font-weight:500;line-height:1.35;'
               f'padding:8px 22px 10px;border-radius:10px;background:#12130fd6">{esc(text)}</span></div>')

    print(f"typesetting {len(sp.specs)} sprites in Chrome ...")
    sp.render(WORK / "sprites")

    # ---- frame renderer
    starts = [c["g0"] for c in chapters]

    def render_beat(beat, t):
        if isinstance(beat.src, Scene):
            return beat.src.render(t), None
        state = beat_state(beat, t)
        frame = camera(beat.src, state)
        return frame, state

    def visual(ci, t):
        bs = chapters[ci]["beats"]
        i = max(k for k, b in enumerate(bs) if b.t <= t or k == 0)
        beat = bs[i]
        frame, state = render_beat(beat, t)
        if beat.hl and state:
            frame = spotlight(frame, to_screen(beat.hl, state), ease_out((t - beat.t - 0.45) / 0.35))
        if i and t - beat.t < 0.45:
            prev = bs[i - 1]
            if prev.src is not beat.src:
                old, old_state = render_beat(prev, t)
                if prev.hl and old_state:
                    old = spotlight(old, to_screen(prev.hl, old_state), 1.0)
                frame = Image.blend(old, frame, ease_in_out((t - beat.t) / 0.45))
            elif prev.hl and state:
                frame = spotlight(frame, to_screen(prev.hl, state), 1 - (t - beat.t) / 0.25)
        return frame, isinstance(beat.src, Scene)

    def overlay(frame, img_pos, alpha=1.0):
        img, (x, y) = img_pos
        if alpha <= 0:
            return
        if alpha < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        frame.alpha_composite(img, (x, y))

    def frame_at(gt):
        if gt < hook:
            for a, b, src, s0, s1, hl in hook_shots:
                if a <= gt < b:
                    p = (gt - a) / (b - a)
                    if isinstance(src, Scene):
                        frame = src.render(1e9 if src is evaluation else gt - a)
                    else:
                        state = lerp_state(s0, s1, ease_out(p))
                        frame = camera(src, state)
                        if hl:
                            frame = spotlight(frame, to_screen(hl, state), 1.0)
                    return frame
        ci = bisect.bisect_right(starts, gt) - 1
        c = chapters[ci]
        lt = gt - c["g0"]
        frame, is_scene = visual(ci, lt)
        frame = frame.convert("RGBA")
        if ci and lt < 1.7:
            card, _ = sp[f"card-{ci}"]
            p_in, p_out = ease_out(lt / 0.35), ease_in_out((lt - 1.3) / 0.4)
            top, bottom = int(H * (1 - p_in)), int(H * (1 - p_out))
            if bottom > top:
                piece = card.crop((0, top, W, bottom))
                frame.alpha_composite(piece, (0, top))
        elif ci and not is_scene:
            img, (x, y) = sp[f"label-{ci}"]
            overlay(frame, (img, (20 + x, 18 + y)), ease_out((lt - 1.7) / 0.3))
        for k, (a, b, _) in enumerate(cues):
            if a <= gt < b:
                img, (x, y) = sp[f"cap-{k}"]
                overlay(frame, (img, (x, H - 96 + y - 10)), ease_out((gt - a) / 0.12))
                break
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, H - 4, W, H), fill=(228, 223, 218, 30))
        draw.rectangle((0, H - 4, int(W * (gt - hook) / (total - hook)), H), fill=TEAL + (255,))
        for g in starts[1:]:
            x = int(W * (g - hook) / (total - hook))
            draw.rectangle((x - 1, H - 4, x + 1, H), fill=BG + (255,))
        frame = frame.convert("RGB")
        if gt > total - 0.7:
            frame = Image.blend(frame, Image.new("RGB", (W, H), BG), (gt - (total - 0.7)) / 0.7)
        return frame

    if args.preview:
        out = WORK / "preview"
        out.mkdir(exist_ok=True)
        for sec in (float(x) for x in args.preview.split(",")):
            frame_at(sec).save(out / f"t{sec:07.2f}.png")
        print(f"preview stills in {out}")
        return

    # ---- audio mix
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for c in chapters:
        a = int((c["g0"] + c["pre"]) * SR)
        voice[a : a + len(c["audio"])] += c["audio"]
    voice *= 0.72 / (np.abs(voice).max() + 1e-9)
    mix = voice.copy()
    if not args.no_music:
        block = SR // 100
        level = np.abs(voice[: len(voice) // block * block]).reshape(-1, block).max(1)
        env, smooth = 0.0, np.zeros_like(level)
        for i, v in enumerate(level > 0.02):
            env += (1 - env) * 0.3 if v else -env * 0.012
            smooth[i] = env
        duck = np.repeat(smooth, block)
        duck = np.pad(duck, (0, len(voice) - len(duck)))
        music = pad_music(len(voice) / SR)
        gain = 10 ** ((-19 - 11 * duck) / 20)
        t = np.arange(len(voice)) / SR
        gain *= np.clip(t / 1.0, 0, 1) * np.clip((total - t) / 2.5, 0, 1)
        mix += music * gain.astype(np.float32)
        rng = np.random.default_rng(7)
        for at in [0.9, 1.7, 2.5, 3.4] + [c["g0"] for c in chapters[1:]] + [chapters[7]["g0"] + tm(7, 22.5)]:
            w = whoosh(rng) * 0.16
            a = int(max(0, at - 0.45) * SR)
            mix[a : a + len(w)] += w[: len(mix) - a]
    mix *= 0.95 / max(0.95, np.abs(mix).max())
    write_wav(WORK / "mix.wav", mix)

    # ---- subtitles and chapters for the container
    def srt_time(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    (WORK / "captions.srt").write_text("\n".join(
        f"{k + 1}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n" for k, (a, b, text) in enumerate(cues)), encoding="utf-8")
    meta = [";FFMETADATA1"]
    for i, c in enumerate(chapters):
        a = 0 if i == 0 else c["g0"]
        b = c["g0"] + c["len"]
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(a * 1000)}", f"END={int(b * 1000)}", f"title={c['title']}"]
    (WORK / "chapters.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")

    # ---- encode (captions are burned in; a soft track would double them in
    # players that show it regardless of disposition)
    frames = int(total * FPS)
    encoder = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(WORK / "mix.wav"), "-f", "ffmetadata", "-i", str(WORK / "chapters.txt"),
        "-map", "0:v", "-map", "1:a", "-map_chapters", "2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{frames / FPS:.3f}", args.out],
        stdin=subprocess.PIPE)
    for n in range(frames):
        encoder.stdin.write(frame_at(n / FPS).tobytes())
        if n % (FPS * 15) == 0:
            print(f"  {n / FPS:6.1f}s / {total:.1f}s", flush=True)
    encoder.stdin.close()
    encoder.wait()
    print(f"wrote {args.out}")


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required")
    main()
