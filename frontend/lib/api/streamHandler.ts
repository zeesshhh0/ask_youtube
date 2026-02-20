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
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let isCompleted = false;

    const processLine = (line: string) => {
      const trimmedLine = line.trim();
      if (!trimmedLine || !trimmedLine.startsWith("data:")) return;

      const data = trimmedLine.substring(5).trim();
      if (!data || data === "[DONE]") return;

      try {
        const event: StreamEvent = JSON.parse(data);

        if (event.type === "token" && typeof event.content === "string") {
          onToken(event.content);
        } else if (event.type === "end") {
          isCompleted = true;
          onComplete();
        }
      } catch (parseError) {
        // Only log if it's not a common non-JSON SSE message
        if (!data.startsWith("{")) {
          return; 
        }
        console.warn("Failed to parse SSE JSON:", data, parseError);
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split(/\r?\n/);
        // Keep the last partial line in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          processLine(line);
          if (isCompleted) break;
        }

        if (isCompleted) break;
      }

      // Process any remaining data in the buffer
      if (!isCompleted && buffer) {
        processLine(buffer);
      }
    } finally {
      reader.releaseLock();
    }

    // Always ensure onComplete is called if we haven't already
    if (!isCompleted) {
      onComplete();
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return;
    }
    onError(error instanceof Error ? error : new Error("Stream failed"));
  }
}

/** Create an AbortController for stream cancellation */
export function createStreamController(): AbortController {
  return new AbortController();
}
