import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

// GET /api/chat/[threadId]/history - Get thread history
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ threadId: string }> }
) {
  const { threadId } = await params;

  try {
    const response = await fetch(`${config.apiUrl}/chat/${threadId}/history`);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Get thread history error:", error);
    return NextResponse.json(
      { error: "Failed to get thread history" },
      { status: 500 }
    );
  }
}
