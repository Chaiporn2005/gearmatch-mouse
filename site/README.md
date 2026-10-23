# GearMatch web application

Thai/English mouse recommendation interface with catalog search, explicit hard filters, compare view, source details and a live native-tool-calling class-proxy agent.

```bash
npm ci
npm run dev
```

Set OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL=gemma-4-E4B-it in untracked .dev.vars for local Cloudflare development, or in the production hosting secret store. Do not put them in client code or hosting.json.

- app/page.tsx: user interface
- app/api/: REST endpoints
- lib/gearmatch.ts: retrieval, strict Zod schemas and bounded agent
- lib/catalog.json: generated copy of the canonical parent data/catalog.json
- .openai/hosting.json: retained Site identity and hosting bindings

The full capstone README, canonical Python SDK application, reproducible retrieval evaluation, source provenance and report are in the parent project. This web runtime uses the OpenAI-compatible HTTP protocol and checks retrieval parity against the Python implementation on30 cases. Production builds preserve the Sites/Vinext hosting integration from the retained starter.
