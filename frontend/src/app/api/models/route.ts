import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest): Promise<NextResponse> {
  // For OneSeek.ai, we use FastAPI backend, not direct vLLM connection
  // Return a default model configuration
  const envModel = process.env.VLLM_MODEL || "llama3-8b";
  
  return NextResponse.json({
    object: "list",
    data: [
      {
        id: envModel,
        object: "model",
        created: Date.now(),
        owned_by: "oneseek",
      },
    ],
  });
}
