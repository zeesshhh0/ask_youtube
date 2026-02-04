import type { StreamEvent } from "@/lib/types";

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onSources?: (
    chunks: Array<{ text: string; start_time?: number; end_time?: number }>
  ) => void;
  onComplete: (messageId: number) => void;
  onError: (error: Error) => void;
}

/**
 * Handle SSE stream from the chat API
 * Uses fetch with ReadableStream for better control
 */
export async function handleSSEStream(
  url: string,
  payload: { content: string; video_id: string },
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const { onToken, onSources, onComplete, onError } = callbacks;

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

      // Process complete SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6);
          if (jsonStr === "[DONE]") {
            continue;
          }

          try {
            const event: StreamEvent = JSON.parse(jsonStr);

            switch (event.type) {
              case "token":
                onToken(event.content);
                break;
              case "sources":
                onSources?.(event.chunks);
                break;
              case "end":
                onComplete(event.message_id);
                return;
              case "error":
                onError(new Error(event.message));
                return;
            }
          } catch (parseError) {
            console.warn("Failed to parse SSE event:", jsonStr, parseError);
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      // Stream was intentionally aborted
      return;
    }
    onError(error instanceof Error ? error : new Error("Stream failed"));
  }
}

/**
 * Create an abort controller for stream cancellation
 */
export function createStreamController(): AbortController {
  return new AbortController();
}
