"use client";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  SlidersHorizontal,
  Mouse,
  Sparkles,
  X,
  Plus,
  Activity,
  ShieldCheck,
  BookOpen,
  LoaderCircle,
  RotateCcw,
  Search,
} from "lucide-react";
type P = {
  id: string;
  name: string;
  brand: string;
  price: number | null;
  weight_g: number | null;
  connection: string[];
  handedness: string | null;
  shape: string | null;
  features: string[];
  specs: { max_dpi?: number | null; max_polling_hz?: number | null };
  variant: string;
  notes: string;
  price_basis: string;
  source_excerpt: string;
  sources: { url: string; title: string }[];
  use_cases: string[];
};
type F = {
  budget: number | null;
  max_weight: number | null;
  connection: string | null;
  handedness: string | null;
  use_case: string | null;
};
const initial: F = {
  budget: 150,
  max_weight: null,
  connection: null,
  handedness: null,
  use_case: null,
};
const prompts = [
  "เมาส์เงียบสำหรับทำงาน ใช้ Bluetooth",
  "เมาส์เล่นเกมเบา งบ 70 USD",
  "เมาส์แนวตั้งสำหรับคนถนัดซ้าย",
];
function price(n: number | null) {
  return n == null ? "ไม่ทราบ" : "$" + n.toFixed(2);
}
function Art({ p, large = false }: { p: P; large?: boolean }) {
  const color =
    p.brand === "Keychron"
      ? "#c7d1d5"
      : p.name.includes("Pebble")
        ? "#b5bda8"
        : p.name.includes("Lift")
          ? "#9d9eb0"
          : "#303b40";
  return (
    <svg
      className={"mouse-art " + (large ? "large" : "")}
      viewBox="0 0 240 200"
      role="img"
      aria-label={"ภาพสัญลักษณ์ " + p.name}
    >
      <defs>
        <linearGradient id={"b" + p.id}>
          <stop stopColor={color} />
          <stop
            offset="1"
            stopColor={p.brand === "Keychron" ? "#8b999f" : "#172126"}
          />
        </linearGradient>
        <filter id={"s" + p.id}>
          <feDropShadow dx="3" dy="13" stdDeviation="8" floodOpacity=".17" />
        </filter>
      </defs>
      <ellipse cx="123" cy="174" rx="60" ry="8" fill="#182518" opacity=".04" />
      {p.connection.length === 1 && p.connection[0] === "wired" && (
        <path
          d="M120 48 C127 19 90 18 101 0"
          fill="none"
          stroke="#717974"
          strokeWidth="3"
        />
      )}
      <g
        transform={
          p.shape === "vertical" ? "rotate(-28 120 110)" : "rotate(-18 120 110)"
        }
        filter={"url(#s" + p.id + ")"}
      >
        <path
          d={
            p.shape === "vertical"
              ? "M92 60 C109 31 146 44 157 77 L173 133 C179 162 154 174 115 172 C80 169 64 153 73 123 Z"
              : "M77 88 C78 38 159 36 166 87 L171 133 C175 185 68 185 72 133 Z"
          }
          fill={"url(#b" + p.id + ")"}
          stroke="#000"
          strokeOpacity=".1"
        />
        <path
          d="M120 49L120 106 M78 103Q120 116 168 103"
          stroke="#172126"
          opacity=".5"
          fill="none"
        />
        <rect x="115" y="65" width="10" height="24" rx="5" fill="#152027" />
        <path d="M118 70L122 70M118 75L122 75M118 80L122 80" stroke="#7b878a" />
        {p.use_cases.includes("gaming") && (
          <path
            d="M116 143L123 150L128 140"
            stroke={p.brand === "Razer" ? "#b6f66a" : "#f48a67"}
            fill="none"
            strokeWidth="2"
          />
        )}
        <path
          d="M78 115L78 130"
          stroke="#83918d"
          strokeWidth="3"
          strokeLinecap="round"
          opacity=".5"
        />
      </g>
    </svg>
  );
}
export default function Home() {
  const [products, setProducts] = useState<P[]>([]),
    [filters, setFilters] = useState(initial),
    [query, setQuery] = useState(""),
    [tab, setTab] = useState("all"),
    [selected, setSelected] = useState<string[]>([]),
    [detail, setDetail] = useState<P | null>(null),
    [result, setResult] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [configured, setConfigured] = useState(false),
    [view, setView] = useState("discover");
  useEffect(() => {
    fetch("/api/catalog")
      .then((r) => r.json())
      .then((d: any) => setProducts(d.products))
      .catch(() => setError("โหลด catalog ไม่สำเร็จ"));
    fetch("/api/health")
      .then((r) => r.json())
      .then((d: any) => setConfigured(d.llm_configured))
      .catch(() => {});
  }, []);
  const visible = products.filter(
    (p) =>
      (filters.budget == null ||
        (p.price != null && p.price <= filters.budget)) &&
      (filters.max_weight == null ||
        (p.weight_g != null && p.weight_g <= filters.max_weight)) &&
      (!filters.connection || p.connection.includes(filters.connection)) &&
      (!filters.handedness || p.handedness === filters.handedness) &&
      (!filters.use_case || p.use_cases.includes(filters.use_case)) &&
      (tab === "all" ||
        (tab === "quiet" && p.features.includes("quiet_clicks")) ||
        (tab === "light" && p.weight_g != null && p.weight_g <= 60) ||
        (tab === "vertical" && p.shape === "vertical")),
  );
  function toggle(id: string) {
    setSelected((s) =>
      s.includes(id)
        ? s.filter((x) => x !== id)
        : s.length < 3
          ? [...s, id]
          : s,
    );
  }
  async function ask(mode = "recommend") {
    if (query.trim().length < 2) {
      setError("เล่าความต้องการก่อนเริ่มค้นหาครับ");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const r = await fetch("/api/" + mode, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, filters }),
      });
      const d: any = await r.json();
      if (!r.ok) throw Error(d.error || "ไม่สามารถประมวลผลได้");
      setResult({ ...d, kind: mode });
    } catch (e) {
      setError(e instanceof Error ? e.message : "เกิดข้อผิดพลาด");
    } finally {
      setBusy(false);
    }
  }
  function preset(i: number) {
    setQuery(prompts[i]);
    setFilters(
      i === 0
        ? { ...initial, connection: "bluetooth", use_case: "office" }
        : i === 1
          ? { ...initial, budget: 70, max_weight: 60, use_case: "gaming" }
          : { ...initial, handedness: "left" },
    );
  }
  return (
    <div>
      <header>
        <a className="brand" href="/">
          <span className="brand-icon">
            <Mouse size={21} />
          </span>
          Gear<span>Match</span>
          <small>MOUSE LAB</small>
        </a>
        <nav>
          {["discover", "compare", "about"].map((v) => (
            <button
              key={v}
              className={view === v ? "active" : ""}
              onClick={() => setView(v)}
            >
              {v === "discover"
                ? "Discover"
                : v === "compare"
                  ? "Compare" +
                    (selected.length ? " (" + selected.length + ")" : "")
                  : "About the data"}
            </button>
          ))}
        </nav>
        <div className="status">
          <i className={configured ? "online" : ""} />
          {configured ? "Class proxy connected" : "Catalog ready"}
          <b>21 MICE</b>
        </div>
      </header>
      <main>
        {view === "discover" ? (
          <>
            <section className="hero">
              <div>
                <div className="eyebrow">
                  <i />
                  LESS GUESSWORK. BETTER GEAR.
                </div>
                <h1>
                  Your next mouse.
                  <br />
                  <em>A better match.</em>
                </h1>
                <p>
                  เมาส์ที่ใช่ เริ่มจากสิ่งที่คุณต้องการ
                  <br />
                  ค้นหา เปรียบเทียบ และเลือกจากสเปกที่มีแหล่งอ้างอิงจริง
                </p>
                <div className="hero-badges">
                  <span>
                    <ShieldCheck size={14} />
                    Source-grounded
                  </span>
                  <span>
                    <Activity size={14} />
                    21 curated mice
                  </span>
                  <span>
                    <BookOpen size={14} />
                    Reference USD prices
                  </span>
                </div>
              </div>
              <div className="hero-art">
                <div className="orbit" />
                <div className="orbit two" />
                <span className="cross a">+</span>
                <span className="cross b">+</span>
                {products.length > 0 && (
                  <Art
                    large
                    p={
                      products.find((p) => p.id === "keychron-m2-4k") ||
                      products[0]
                    }
                  />
                )}
                <div className="weight-badge">
                  55<span>g</span>
                  <small>LIGHTER BY DESIGN</small>
                </div>
                <div className="workflow">
                  <i />
                  Built for your workflow
                </div>
                <span className="caption">FIND YOUR EVERYDAY ADVANTAGE ↗</span>
              </div>
            </section>
            <div className="workspace">
              <aside>
                <div className="assistant-head">
                  <span>
                    <Sparkles size={21} />
                  </span>
                  <div>
                    <h2>Your mouse, your way</h2>
                    <p>บอกเรา คุณจะใช้เมาส์ทำอะไร</p>
                  </div>
                </div>
                <label className="sr-only" htmlFor="question">
                  ความต้องการเมาส์
                </label>
                <textarea
                  id="question"
                  maxLength={1500}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="เช่น ทำงานทั้งวัน อยากได้เมาส์เงียบ ใช้กับโน้ตบุ๊กผ่าน Bluetooth..."
                />
                <div className="suggestions">
                  {prompts.map((p, i) => (
                    <button key={p} onClick={() => preset(i)}>
                      <span>↗</span>
                      {p}
                    </button>
                  ))}
                </div>
                <div className="filter-head">
                  <span>
                    <SlidersHorizontal size={14} />
                    YOUR PREFERENCES
                  </span>
                  <button
                    aria-label="รีเซ็ตตัวกรอง"
                    onClick={() => {
                      setFilters(initial);
                      setTab("all");
                    }}
                  >
                    <RotateCcw size={14} />
                  </button>
                </div>
                <div className="budget-label">
                  งบอ้างอิงสูงสุด
                  <strong>
                    {price(filters.budget)}
                    <small> USD</small>
                  </strong>
                </div>
                <input
                  aria-label="งบอ้างอิง USD"
                  type="range"
                  min="10"
                  max="150"
                  step="5"
                  value={filters.budget || 150}
                  onChange={(e) =>
                    setFilters({ ...filters, budget: Number(e.target.value) })
                  }
                />
                <div className="range-label">
                  <span>$10</span>
                  <span>$150</span>
                </div>
                <div className="select-grid">
                  <label>
                    การเชื่อมต่อ
                    <select
                      value={filters.connection || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          connection: e.target.value || null,
                        })
                      }
                    >
                      <option value="">ทุกแบบ</option>
                      <option value="bluetooth">Bluetooth</option>
                      <option value="2.4ghz">2.4 GHz</option>
                      <option value="wired">มีสาย / USB</option>
                    </select>
                  </label>
                  <label>
                    น้ำหนักสูงสุด
                    <select
                      value={filters.max_weight || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          max_weight: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">ไม่จำกัด</option>
                      {[60, 80, 100].map((n) => (
                        <option key={n} value={n}>
                          {n} g
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    มือที่ถนัด
                    <select
                      value={filters.handedness || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          handedness: e.target.value || null,
                        })
                      }
                    >
                      <option value="">ไม่จำกัด</option>
                      <option value="right">มือขวา</option>
                      <option value="left">มือซ้าย</option>
                      <option value="ambidextrous">ทั้งสองมือ</option>
                    </select>
                  </label>
                  <label>
                    การใช้งาน
                    <select
                      value={filters.use_case || ""}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          use_case: e.target.value || null,
                        })
                      }
                    >
                      <option value="">ทุกประเภท</option>
                      <option value="office">ทำงาน</option>
                      <option value="gaming">เล่นเกม</option>
                      <option value="travel">พกพา</option>
                    </select>
                  </label>
                </div>
                <button
                  className="primary ask"
                  disabled={busy}
                  onClick={() => ask()}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Sparkles size={17} />
                  )}
                  Find my match
                  <ArrowRight size={18} />
                </button>
                <button
                  className="search-only"
                  disabled={busy}
                  onClick={() => ask("search")}
                >
                  <Search size={13} />
                  ค้นเฉพาะ catalog โดยไม่ใช้โมเดล
                </button>
                <p className="privacy-note">
                  ราคาอ้างอิง USD ไม่ใช่ราคาไทยหรือราคาปัจจุบัน
                  ไม่มีการซื้อขายผ่านแอป
                </p>
              </aside>
              <section className="catalog">
                <div className="catalog-head">
                  <div>
                    <div className="eyebrow">THE SHORTLIST STARTS HERE</div>
                    <h2>Good gear. Clear choices.</h2>
                  </div>
                  <span>{visible.length} matches</span>
                </div>
                <div className="tabs">
                  {[
                    ["all", "All mice"],
                    ["quiet", "Quiet clicks"],
                    ["light", "Under 60g"],
                    ["vertical", "Vertical"],
                  ].map(([id, name]) => (
                    <button
                      key={id}
                      className={tab === id ? "active" : ""}
                      onClick={() => setTab(id)}
                    >
                      {name}
                    </button>
                  ))}
                  <span>3 brands · curated specs</span>
                </div>
                {error && (
                  <div className="error" role="alert">
                    <strong>ยังแนะนำไม่ได้ในตอนนี้</strong>
                    <p>{error}</p>
                    <button onClick={() => ask("search")}>
                      ลองค้น catalog แทน →
                    </button>
                  </div>
                )}
                {result && (
                  <div className="result">
                    <div className="result-head">
                      <Sparkles size={17} />
                      <strong>
                        {result.kind === "search"
                          ? "Catalog search results"
                          : "Your GearMatch shortlist"}
                      </strong>
                      <small>
                        {result.kind === "search"
                          ? "ไม่ใช่ผลจาก LLM"
                          : result.model}
                      </small>
                      <button
                        aria-label="ปิดผลลัพธ์"
                        onClick={() => setResult(null)}
                      >
                        <X size={15} />
                      </button>
                    </div>
                    {result.kind === "search" ? (
                      <>
                        {result.hits.length ? (
                          result.hits.map((h: any) => (
                            <button
                              key={h.product.id}
                              className="hit"
                              onClick={() => setDetail(h.product)}
                            >
                              {h.product.name}
                              <span>{price(h.product.price)} ↗</span>
                            </button>
                          ))
                        ) : (
                          <p>ไม่พบสินค้าในเงื่อนไข ลองปรับข้อกำหนด</p>
                        )}
                      </>
                    ) : (
                      <>
                        <p>{result.answer.summary}</p>
                        {result.answer.recommendations.map((r: any) => {
                          const p = result.evidence.find(
                            (p: P) => p.id === r.product_id,
                          );
                          return (
                            <div className="recommendation" key={r.product_id}>
                              <strong>{p?.name}</strong>
                              <p>{r.reason}</p>
                              <small>ข้อควรพิจารณา: {r.tradeoff}</small>
                              <button onClick={() => setDetail(p)}>
                                ดูหลักฐานและสเปก ↗
                              </button>
                            </div>
                          );
                        })}
                        {result.answer.limitations.map((t: string) => (
                          <p className="note" key={t}>
                            {t}
                          </p>
                        ))}
                        <details>
                          <summary>
                            เส้นทางการค้นข้อมูล · {result.trace.length} tool
                            calls
                          </summary>
                          {result.trace.map((t: any, i: number) => (
                            <p className="trace" key={i}>
                              {t.tool}: {t.query || t.error} ·{" "}
                              {t.product_ids?.length || 0} results
                            </p>
                          ))}
                        </details>
                      </>
                    )}
                  </div>
                )}
                <div className="product-grid">
                  {visible.map((p, i) => (
                    <article className="card" key={p.id}>
                      <div className={"product-image tone" + (i % 4)}>
                        <span className="tag">
                          {p.features.includes("quiet_clicks")
                            ? "QUIET CLICKS"
                            : p.weight_g != null && p.weight_g <= 60
                              ? "LIGHTWEIGHT"
                              : p.shape === "vertical"
                                ? "VERTICAL"
                                : p.use_cases.includes("gaming")
                                  ? "PLAY READY"
                                  : "EVERYDAY"}
                        </span>
                        <button
                          className={
                            "compare-toggle " +
                            (selected.includes(p.id) ? "selected" : "")
                          }
                          aria-label={"เปรียบเทียบ " + p.name}
                          aria-pressed={selected.includes(p.id)}
                          onClick={() => toggle(p.id)}
                        >
                          {selected.includes(p.id) ? (
                            <Check size={16} />
                          ) : (
                            <Plus size={16} />
                          )}
                        </button>
                        <button
                          className="art-button"
                          onClick={() => setDetail(p)}
                          aria-label={"ดูสเปก " + p.name}
                        >
                          <Art p={p} />
                        </button>
                      </div>
                      <div className="product-info">
                        <span className="product-brand">
                          {p.brand.toUpperCase()}
                        </span>
                        <h3>
                          <button onClick={() => setDetail(p)}>
                            {p.name.replace(p.brand + " ", "")}
                          </button>
                        </h3>
                        <div className="quick-specs">
                          <span>
                            {p.weight_g != null
                              ? p.weight_g + " g"
                              : "Weight n/a"}
                          </span>
                          <i />
                          <span>
                            {p.connection.includes("bluetooth")
                              ? "Bluetooth + 2.4 GHz"
                              : p.connection.includes("2.4ghz")
                                ? "2.4 GHz wireless"
                                : "Wired USB"}
                          </span>
                        </div>
                        <div className="product-bottom">
                          <strong>
                            {price(p.price)}
                            <small> USD ref.</small>
                          </strong>
                          <button
                            aria-label={"รายละเอียด " + p.name}
                            onClick={() => setDetail(p)}
                          >
                            <ArrowUpRight size={18} />
                          </button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
                {!visible.length && (
                  <div className="empty">
                    <Mouse size={40} />
                    <h3>ยังไม่มีรุ่นที่ตรงทุกเงื่อนไข</h3>
                    <p>เราไม่เติมสเปกที่ไม่ทราบ ลองลดข้อจำกัดแล้วค้นใหม่</p>
                    <button
                      className="primary"
                      onClick={() => {
                        setFilters(initial);
                        setTab("all");
                      }}
                    >
                      รีเซ็ตตัวกรอง
                    </button>
                  </div>
                )}
              </section>
            </div>
          </>
        ) : view === "compare" ? (
          <section className="secondary">
            <div className="eyebrow">SIDE BY SIDE</div>
            <h1>Compare your shortlist.</h1>
            <p>เลือกได้สูงสุด 3 รุ่นจากหน้า Discover</p>
            {selected.length ? (
              <div className="comparison">
                {products
                  .filter((p) => selected.includes(p.id))
                  .map((p) => (
                    <article key={p.id}>
                      <Art p={p} />
                      <h2>{p.name}</h2>
                      <button onClick={() => toggle(p.id)}>นำออก ×</button>
                      <dl>
                        {[
                          ["ราคาอ้างอิง", price(p.price) + " USD"],
                          [
                            "น้ำหนัก",
                            p.weight_g != null ? p.weight_g + " g" : "ไม่ทราบ",
                          ],
                          ["การเชื่อมต่อ", p.connection.join(", ")],
                          ["มือที่ถนัด", p.handedness || "ไม่ทราบ"],
                          [
                            "DPI สูงสุด",
                            p.specs.max_dpi?.toLocaleString() || "ไม่ทราบ",
                          ],
                          [
                            "Polling สูงสุด",
                            p.specs.max_polling_hz
                              ? p.specs.max_polling_hz + " Hz"
                              : "ไม่ทราบ",
                          ],
                        ].map(([k, v]) => (
                          <div key={k}>
                            <dt>{k}</dt>
                            <dd>{v}</dd>
                          </div>
                        ))}
                      </dl>
                      <p className="variant">{p.variant}</p>
                      <button onClick={() => setDetail(p)}>
                        แหล่งอ้างอิง ↗
                      </button>
                    </article>
                  ))}
              </div>
            ) : (
              <div className="empty">
                <Mouse size={40} />
                <h3>เริ่มจากเลือกเมาส์ที่สนใจ</h3>
                <button className="primary" onClick={() => setView("discover")}>
                  กลับไปเลือกเมาส์
                </button>
              </div>
            )}
          </section>
        ) : (
          <section className="secondary">
            <div className="eyebrow">EVIDENCE OVER GUESSWORK</div>
            <h1>
              Know what goes
              <br />
              into your match.
            </h1>
            <div className="about-grid">
              {[
                [
                  "01",
                  "A small, traceable catalog",
                  "21 รุ่นจาก Logitech, Keychron และ Razer ตรวจจากเว็บไซต์ผู้ผลิตวันที่ 24 ตุลาคม 2026 แยก variant และเก็บแหล่งอ้างอิงทุกสินค้า",
                ],
                [
                  "02",
                  "Reference prices, clearly labeled",
                  "ราคาอ้างอิง USD ตามหน้าผู้ผลิต ส่วน Razer Cobra ใช้ราคาเปิดตัวปี 2023 ไม่ใช่ราคาปัจจุบัน ไม่รวมภาษีหรือขนส่ง และไม่มีการแปลงเป็นราคาไทย",
                ],
                [
                  "03",
                  "Unknown means unknown",
                  "สเปกที่ยืนยันไม่ได้เก็บเป็น null และไม่ผ่านตัวกรองที่ต้องใช้ค่านั้น น้ำหนักอาจรวมหรือไม่รวมสาย/แบตเตอรี่ต่างกัน โปรดอ่านหมายเหตุแต่ละรุ่น",
                ],
                [
                  "04",
                  "An honest AI assistant",
                  "เมื่อเชื่อม class proxy แล้ว agent จะเรียกเครื่องมือค้นข้อมูล ตรวจ schema และตรวจว่ารุ่นที่แนะนำมีหลักฐานและผ่านตัวกรอง การค้น catalog ปกติไม่ใช่ผลจาก LLM",
                ],
              ].map(([n, h, p]) => (
                <article key={n}>
                  <span>{n}</span>
                  <h2>{h}</h2>
                  <p>{p}</p>
                </article>
              ))}
            </div>
            <p className="data-note">
              ภาพเมาส์เป็นภาพสัญลักษณ์วาดด้วยโค้ด ไม่ใช่ภาพสินค้าจริง
              ข้อมูลนี้ไม่ใช่การทดสอบประสิทธิภาพหรือคำแนะนำทางการแพทย์
            </p>
          </section>
        )}
      </main>
      <footer>
        <span className="footer-brand">
          GearMatch<small> / MOUSE LAB</small>
        </span>
        <p>A little more evidence. A lot less guesswork.</p>
        <span>DATA SNAPSHOT · OCT 2026</span>
      </footer>
      {selected.length > 0 && view === "discover" && (
        <div className="compare-bar">
          <span>
            <Mouse size={17} />
            {selected.length} mice on your shortlist
          </span>
          <button onClick={() => setView("compare")}>
            Compare now
            <ArrowRight size={16} />
          </button>
        </div>
      )}
      {detail && (
        <div className="backdrop" onClick={() => setDetail(null)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={detail.name}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close"
              aria-label="ปิดรายละเอียด"
              onClick={() => setDetail(null)}
            >
              <X />
            </button>
            <div className="detail-art">
              <Art p={detail} large />
            </div>
            <div className="detail-body">
              <div className="eyebrow">{detail.brand} / VERIFIED CATALOG</div>
              <h2>{detail.name}</h2>
              <p className="variant">{detail.variant}</p>
              <strong className="detail-price">
                {price(detail.price)}
                <small> USD reference</small>
              </strong>
              <p>{detail.source_excerpt}</p>
              <div className="features">
                {detail.features.map((f) => (
                  <span key={f}>{f.replaceAll("_", " ")}</span>
                ))}
              </div>
              <h3>Manufacturer sources</h3>
              {detail.sources.map((s) => (
                <a
                  className="source"
                  key={s.url}
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {s.title}
                  <ArrowUpRight size={14} />
                </a>
              ))}
              <p className="data-note">
                {detail.price_basis.includes("launch")
                  ? "ราคาเปิดตัวสหรัฐฯ 29 มิ.ย. 2023"
                  : "ราคาอ้างอิงตามหน้าผู้ผลิต 24 ต.ค. 2026"}{" "}
                · ไม่ใช่ราคาขายปัจจุบัน
              </p>
              <button className="primary" onClick={() => toggle(detail.id)}>
                {selected.includes(detail.id)
                  ? "นำออกจากการเปรียบเทียบ"
                  : "เพิ่มเพื่อเปรียบเทียบ"}
                <Plus size={16} />
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
