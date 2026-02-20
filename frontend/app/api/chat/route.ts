import { NextRequest, NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${config.apiUrl}/api/v1/threads`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Chat init error:", error);
    return NextResponse.json(
      { error: "Failed to initialize chat" },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const response = await fetch(`${config.apiUrl}/api/v1/threads`);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("List threads error:", error);
    return NextResponse.json(
      { error: "Failed to list threads" },
      { status: 500 }
    );
  }
}
