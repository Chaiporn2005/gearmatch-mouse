import { products } from "@/lib/gearmatch";
export async function GET() {
  return Response.json({ products, currency: "USD", checked_on: "2026-10-24" });
}
