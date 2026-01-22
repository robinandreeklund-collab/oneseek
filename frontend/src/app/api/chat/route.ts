import { NextResponse } from "next/server";

// Allow streaming responses up to 60 seconds for RAG operations
export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const { messages, chatOptions } = await req.json();
    
    // Get FastAPI backend URL from environment
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";
    
    // Forward request to FastAPI backend
    const response = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: messages,
        stream: true, // Always stream by default
        system_prompt: chatOptions?.systemPrompt,
        temperature: chatOptions?.temperature || 0.7,
        model: chatOptions?.selectedModel,
        enable_thinking: chatOptions?.enableThinking || false,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend error: ${errorText}`);
      return NextResponse.json(
        {
          success: false,
          error: `Backend returned ${response.status}: ${errorText}`,
        },
        { status: response.status }
      );
    }

    // Stream the response from FastAPI backend to the client
    // The backend sends data in Vercel AI SDK format
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Error in chat route:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
