import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import type {
  CreateThreadResponse,
  ThreadListItem,
  ThreadMessagesResponse,
  DeleteThreadResponse,
} from "@/lib/types";

const BASE = "/api/chat";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || errorData.message || errorData.error || "Request failed",
      response.status,
      errorData
    );
  }
  return response.json();
}

export const apiClient = {
  threads: {
    /**
     * POST /api/chat — ingest a YouTube video and create a new thread.
     */
    create: async (videoUrl: string): Promise<CreateThreadResponse> => {
      const res = await fetch(`${BASE}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl }),
      });
      return handleResponse<CreateThreadResponse>(res);
    },

    /**
     * GET /api/chat — list all threads.
     */
    list: async (): Promise<ThreadListItem[]> => {
      try {
        const res = await fetch(`${BASE}`);
        return handleResponse<ThreadListItem[]>(res);
      } catch {
        return [];
      }
    },

    /**
     * DELETE /api/chat/{thread_id} — delete a thread and its messages.
     */
    delete: async (threadId: string): Promise<DeleteThreadResponse> => {
      const res = await fetch(`${BASE}/${threadId}`, {
        method: "DELETE",
      });
      return handleResponse<DeleteThreadResponse>(res);
    },

    /**
     * GET /api/chat/{thread_id}/history — get full message history.
     */
    getMessages: async (threadId: string): Promise<ThreadMessagesResponse> => {
      const res = await fetch(`${BASE}/${threadId}/history`);
      return handleResponse<ThreadMessagesResponse>(res);
    },

    /**
     * Returns the URL for the SSE message stream endpoint.
     * POST /api/chat/{thread_id}/message — streams AI response via SSE.
     */
    getMessageStreamUrl: (threadId: string): string =>
      `${BASE}/${threadId}/message`,
  },
};
