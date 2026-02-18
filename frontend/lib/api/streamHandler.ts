import type { StreamEvent } from "@/lib/types";

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onComplete: () => void;
  onError: (error: Error) => void;
}

/**
 * Sends a message to POST /api/v1/threads/{threadId}/messages and streams
 * the AI response via SSE using fetch + ReadableStream.
 *
 * The backend emits two event types:
 *   { type: "token", content: string }  — partial AI response chunk
 *   { type: "end" }                     — stream finished
 *
 * NOTE: EventSource is NOT used because it only supports GET requests.
 */
export async function handleSSEStream(
  url: string,
  payload: { content: string },
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const { onToken, onComplete, onError } = callbacks;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split on newlines; keep the last (potentially incomplete) line in buffer
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;

        const jsonStr = line.slice(6).trim();
        if (!jsonStr || jsonStr === "[DONE]") continue;

        try {
          const event: StreamEvent = JSON.parse(jsonStr);

          if (event.type === "token") {
            onToken(event.content);
          } else if (event.type === "end") {
            onComplete();
            return;
          }
        } catch (parseError) {
          console.warn("Failed to parse SSE event:", jsonStr, parseError);
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return; // intentional cancellation
    }
    onError(error instanceof Error ? error : new Error("Stream failed"));
  }
}

/** Create an AbortController for stream cancellation */
export function createStreamController(): AbortController {
  return new AbortController();
}
