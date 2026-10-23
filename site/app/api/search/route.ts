import { requestSchema, search } from "@/lib/gearmatch";
export async function POST(req: Request) {
  try {
    const input = requestSchema.parse(await req.json());
    return Response.json({
      hits: search(input.question, input.filters),
      mode: "catalog_search",
    });
  } catch {
    return Response.json({ error: "Invalid search request" }, { status: 400 });
  }
}
