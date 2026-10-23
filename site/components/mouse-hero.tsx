"use client";
import { useEffect, useRef, useState } from "react";

const WORD = "MOUSE";
// Width per letter (0 = condensed, 1 = expanded). The letters share a fixed
// budget so the word always spans the row: the pointer redistributes width
// rather than adding it. MIN keeps the O from collapsing into a zero.
const MIN = 0.22;
const BUDGET = 2.15;
const REST = [0.55, 0.3, 0.42, 0.32, 0.56];
// Entry stagger mirrors outward from the centre letter.
const ENTRY = [2, 1.4, 1, 1.4, 2];

function Digit({ d }: { d: number }) {
  return (
    <span className="digit" aria-hidden="true">
      <span className="digit-track" style={{ "--d": d } as React.CSSProperties}>
        {"0123456789".split("").map((n) => (
          <span key={n}>{n}</span>
        ))}
      </span>
    </span>
  );
}

function Rolling({ value, size }: { value: number; size: number }) {
  const s = String(Math.max(0, Math.round(value))).padStart(size, "0").slice(-size);
  return (
    <span className="rolling">
      <span className="sr-only">{value}</span>
      {s.split("").map((c, i) => (
        <Digit key={i} d={Number(c)} />
      ))}
    </span>
  );
}

export function MouseHero({ count }: { count: number }) {
  const hero = useRef<HTMLElement>(null);
  const chars = useRef<(HTMLSpanElement | null)[]>([]);
  const xLine = useRef<HTMLDivElement>(null);
  const yLine = useRef<HTMLDivElement>(null);
  const coords = useRef<HTMLSpanElement>(null);
  const [rate, setRate] = useState(0);
  const [clicks, setClicks] = useState(0);

  useEffect(() => {
    const el = hero.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const values = [...REST];
    let pointer: { x: number; y: number } | null = null;
    let frame = 0;
    let events = 0;

    const tick = () => {
      frame = 0;
      let targets = REST;
      if (pointer) {
        const p = pointer;
        const sigma = el.clientWidth * 0.2;
        const pull = chars.current.map((c) => {
          const r = c?.getBoundingClientRect();
          return r ? Math.exp(-(((p.x - (r.left + r.width / 2)) / sigma) ** 2)) + 0.02 : 0;
        });
        const sum = pull.reduce((a, b) => a + b, 0);
        targets = pull.map((w) => Math.min(1, MIN + (w / sum) * (BUDGET - MIN * WORD.length)));
      }
      let moving = false;
      targets.forEach((target, i) => {
        // Exponential approach; settles in ~400ms without overshoot.
        const next = values[i] + (target - values[i]) * 0.14;
        if (Math.abs(target - next) > 0.002) moving = true;
        values[i] = next;
      });
      chars.current.forEach((c, i) => c?.style.setProperty("--f-w", values[i].toFixed(3)));
      if (moving) frame = requestAnimationFrame(tick);
    };
    const schedule = () => {
      if (!frame && !reduce) frame = requestAnimationFrame(tick);
    };

    const move = (e: PointerEvent) => {
      const box = el.getBoundingClientRect();
      const x = e.clientX - box.left;
      const y = e.clientY - box.top;
      pointer = { x: e.clientX, y: e.clientY };
      if (xLine.current) xLine.current.style.transform = `translate3d(0, ${y}px, 0)`;
      if (yLine.current) yLine.current.style.transform = `translate3d(${x}px, 0, 0)`;
      if (coords.current)
        coords.current.textContent =
          String(Math.round(x)).padStart(4, "0") + " × " + String(Math.round(y)).padStart(4, "0");
      el.dataset.pointer = "in";
      schedule();
    };
    const leave = () => {
      pointer = null;
      delete el.dataset.pointer;
      schedule();
    };
    // Rate over the span the pointer was actually moving, so a short flick
    // isn't averaged against idle time.
    let first = 0;
    let last = 0;
    const raw = (e: Event) => {
      if (!events) first = e.timeStamp;
      last = e.timeStamp;
      events++;
    };
    const down = () => setClicks((n) => n + 1);

    // pointerrawupdate fires closer to the device's report rate where supported;
    // pointermove is frame-aligned, so it is only a fallback.
    const rawType = "onpointerrawupdate" in window ? "pointerrawupdate" : "pointermove";
    el.addEventListener("pointermove", move);
    el.addEventListener(rawType, raw);
    el.addEventListener("pointerleave", leave);
    el.addEventListener("pointerdown", down);
    const sample = window.setInterval(() => {
      if (events > 8 && last > first) setRate(Math.round(((events - 1) * 1000) / (last - first)));
      events = 0;
    }, 500);
    return () => {
      cancelAnimationFrame(frame);
      window.clearInterval(sample);
      el.removeEventListener("pointermove", move);
      el.removeEventListener(rawType, raw);
      el.removeEventListener("pointerleave", leave);
      el.removeEventListener("pointerdown", down);
    };
  }, []);

  return (
    <section className="hero" ref={hero}>
      <div className="crosshair" aria-hidden="true">
        <div className="cross-x" ref={xLine} />
        <div className="cross-y" ref={yLine} />
      </div>
      <h1 className="sr-only">GearMatch — find your next mouse</h1>
      <div className="wordmark" aria-hidden="true">
        {WORD.split("").map((c, i) => (
          <span
            key={i}
            className="char"
            ref={(n) => {
              chars.current[i] = n;
            }}
            style={{ "--i": i, "--rt": ENTRY[i], "--f-w": REST[i] } as React.CSSProperties}
          >
            {c}
          </span>
        ))}
      </div>
      <div className="hero-foot">
        <dl className="readouts">
          <div>
            <dt>CURSOR (PX)</dt>
            <dd>
              <span ref={coords}>0000 × 0000</span>
            </dd>
          </div>
          <div>
            <dt>POINTER EVENTS / SEC</dt>
            <dd>
              <Rolling value={rate} size={4} />
              <small>Hz</small>
            </dd>
          </div>
          <div>
            <dt>CLICKS</dt>
            <dd>
              <Rolling value={clicks} size={3} />
            </dd>
          </div>
        </dl>
        <div className="hero-copy">
          <p>
            GearMatch matches you with a mouse by <em>grip</em>, <em>weight</em> and{" "}
            <em>budget</em>, with every spec traced to the maker.
          </p>
          <p className="thai">
            เมาส์ที่ใช่ เริ่มจากสิ่งที่คุณต้องการ ค้นหา เปรียบเทียบ และเลือกจากสเปกที่มีแหล่งอ้างอิงจริง
          </p>
          <a className="link cta" href="#workspace">
            ↳ Find my match · {count} mice
          </a>
        </div>
      </div>
    </section>
  );
}
