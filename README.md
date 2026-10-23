# GearMatch - Mouse Lab

An original mouse-domain capstone: ask in Thai or English, apply explicit product constraints, compare up to three mice and inspect manufacturer evidence. This is not a reskin of the course reference corpus.

## Quick start

Python3.12+ and Node22.13+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set the class proxy's OPENAI_API_KEY and OPENAI_BASE_URL in .env.
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The Python API uses `from openai import OpenAI; OpenAI()`, model `gemma-4-E4B-it`, native Chat Completions tools and temperature0. It does not depend on provider response_format. The class proxy may ignore that option, so JSON is parsed and validated locally.

Run the web app in another terminal:

```bash
cd site
npm ci
npm run dev
```

The web app is Sites-hostable on Cloudflare Workers and includes a TypeScript implementation of the API. For local Worker development, copy the three environment settings to an untracked `site/.dev.vars`; production values must be set as hosting runtime secrets. Its OpenAI-compatible HTTP requests use the same model, tool contract, catalog and guardrails. The Python API is the canonical course SDK/evaluation implementation. The web implementation is checked separately for retrieval parity.

Without class-proxy settings, recommendation requests return an explicit configuration error. Catalog search still works and is labeled as non-LLM; it does not count as a live LLM demonstration.

## Reproduce verification

```bash
python -m unittest discover -s tests -v
python -m evaluation.run
python -m evaluation.live  # 3 real proxy smoke cases; requires .env and network
cd site
npx tsc --noEmit
npm run build
```

Offline metrics and per-case retrievals are in [evaluation/results.json](evaluation/results.json) and [RESULTS.md](evaluation/RESULTS.md). Gold questions have explicit IDs, relevance labels and rationales. Live smoke results are separate in [live-results.json](evaluation/live-results.json); no offline number is represented as an LLM score. The pre-repair failed live run is retained in `evaluation/live-before-fix.json`.

## Architecture and course coverage

1. UI collects a question plus hard filters: USD reference budget, nominal maximum weight, connection, handedness and use case.
2. The model must request an allow-listed native function (`search_specs` or `filter_products`). Arguments are schema-validated; no shell, arbitrary URL or database write can be executed.
3. BM25 and local TF-IDF cosine vectors retrieve from the same 21-product corpus; reciprocal rank fusion uses k=60. Explicit metadata constraints are applied first. Fixed Thai/English domain aliases improve vocabulary overlap. These are lexical vectors, not a pretrained semantic embedding model.
4. Tool observations are data, not instructions. Five model turns maximum, four calls per turn, repeated-query detection. A final answer must pass Pydantic/Zod schemas, product evidence checks, citation-ID checks and hard-filter checks. Repair is bounded.
5. The UI links verified product IDs to recorded manufacturer URLs. Unknown facts remain null. ID checks do not prove every word of the model's free-text explanation is entailed; manual faithfulness review is still needed.

| Course family | Implementation |
|---|---|
| Structured output | Pydantic/Zod input, tool and answer validation plus bounded JSON repair |
| Retrieval/RAG | Corpus, local lexical-vector index, BM25, RRF and citations |
| Evaluation (required) | 30 labeled examples, Recall@3, MRR@3, baseline and ablation |
| Agentic loop (required) | Native function call, execute/feed-back and stop condition |
| Served interface | Python FastAPI and web application with hosted REST API |

## Evaluation protocol

Thirty author-curated cases: 20 development and 10 held-out examples, with24 answerable and6 unanswerable. Relevance IDs were committed in the gold file before evaluation. There is no independent annotator, statistical-significance claim or general market benchmark. One query has four relevant products, so its maximum Recall@3 is0.75.

- Baseline: BM25 without explicit filters or bilingual expansion.
- Ablation: filtered BM25, separating constraint effects from other changes.
- Improved: filtered BM25 + TF-IDF cosine RRF + fixed bilingual aliases.

The combined experiment does not isolate vector fusion from alias expansion. Retrieval metrics do not establish response faithfulness, comfort, latency, purchase satisfaction or current market coverage. A small live smoke suite checks the real tool loop separately.

## Data, pricing and limitations

Read [data provenance](data/README.md). There are21 mouse SKUs from Logitech, Keychron and Razer and33 official source records, checked2026-10-24. USD reference prices are not live Thai retail prices and not consistently MSRP. Razer Cobra uses explicitly dated2023 launch MSRP. No tax, shipping, stock or currency conversion is asserted.

null means unverified, not false or zero. Charging alone does not imply wired data. Manufacturer weights differ in cable/battery inclusion and tolerances. Unknown handedness does not pass a handedness filter. Variant names prevent mixing a cheap model's price with a flagship sensor claim. Mouse drawings are original schematic illustrations, not product photographs. Manufacturer positioning is not independent performance or medical evidence.

## Repository

```text
app/          Python API, schemas, retrieval and bounded agent
data/         Catalog, source manifest and original factual research notes
evaluation/   Gold set, reproducible metrics and live traces
tests/        Unit, agent-contract and API tests
site/         Web UI and Cloudflare-hostable API
docs/         Report, demonstration script and submission status
scripts/      Report and runtime-parity utilities
```

Keep .env, .dev.vars, credentials, runtime caches and node_modules out of Git. Read secrets only from the environment. The student must inspect the code and labels and defend one design choice and one evaluation number live. AI assistance was used for implementation, source research and test generation; results are measured, not invented.

OpenAI tool round-trip reference: https://developers.openai.com/api/docs/guides/function-calling

## License

Project code is MIT licensed. Manufacturer content/trademarks, third-party dependencies and the retained Sites starter keep their respective licenses. No full manufacturer page, logo or product image is redistributed.
