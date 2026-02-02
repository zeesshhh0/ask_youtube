import { NextRequest } from "next/server";
import { config } from "@/lib/config";

// POST /api/chat/[threadId]/message - Send message and stream response
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ threadId: string }> }
) {
  const { threadId } = await params;
  const body = await request.json();

  try {
    const response = await fetch(`${config.apiUrl}/chat/${threadId}/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || "Failed to send message" },
        { status: response.status }
      );
    }

    // Forward the SSE stream
    const stream = response.body;
    if (!stream) {
      return Response.json({ error: "No response stream" }, { status: 500 });
    }

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Message streaming error:", error);
    return Response.json(
      { error: "Failed to send message" },
      { status: 500 }
    );
  }
}
