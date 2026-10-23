import { env } from "cloudflare:workers";
export async function GET() {
  const e = env as Record<string, string>;
  return Response.json({
    ok: true,
    llm_configured: Boolean(e.OPENAI_API_KEY && e.OPENAI_BASE_URL),
    model: e.OPENAI_MODEL || "gemma-4-E4B-it",
  });
}
