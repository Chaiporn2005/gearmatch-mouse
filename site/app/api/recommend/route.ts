import { requestSchema, runAgent } from "@/lib/gearmatch";
import { env } from "cloudflare:workers";
export async function POST(req: Request) {
  let input;
  try {
    input = requestSchema.parse(await req.json());
  } catch {
    return Response.json(
      { error: "Invalid question or filters" },
      { status: 400 },
    );
  }
  try {
    return Response.json(await runAgent(input, env as any));
  } catch (e) {
    const code = e instanceof Error ? e.message : "AGENT_ERROR";
    return Response.json(
      {
        error:
          code === "CLASS_PROXY_NOT_CONFIGURED"
            ? "ยังไม่ได้ตั้งค่า class proxy บนเซิร์ฟเวอร์ ใช้การค้น catalog ได้ แต่ยังไม่ใช่คำตอบจาก LLM"
            : "โมเดลยังไม่สามารถคืนคำตอบที่ผ่านการตรวจสอบได้ ลองระบุความต้องการให้ชัดขึ้น",
        code,
      },
      { status: code === "CLASS_PROXY_NOT_CONFIGURED" ? 503 : 502 },
    );
  }
}
