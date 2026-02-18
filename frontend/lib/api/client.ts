import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import type {
  CreateThreadResponse,
  ThreadListItem,
  ThreadMessagesResponse,
  DeleteThreadResponse,
} from "@/lib/types";

const BASE = `${config.apiUrl}/api/v1`;

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.detail || errorData.message || "Request failed",
      response.status,
      errorData
    );
  }
  return response.json();
}

export const apiClient = {
  threads: {
    /**
     * POST /api/v1/threads — ingest a YouTube video and create a new thread.
     */
    create: async (videoUrl: string): Promise<CreateThreadResponse> => {
      const res = await fetch(`${BASE}/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl }),
      });
      return handleResponse<CreateThreadResponse>(res);
    },

    /**
     * GET /api/v1/threads — list all threads.
     */
    list: async (): Promise<ThreadListItem[]> => {
      try {
        const res = await fetch(`${BASE}/threads`);
        return handleResponse<ThreadListItem[]>(res);
      } catch {
        return [];
      }
    },

    /**
     * DELETE /api/v1/threads/{thread_id} — delete a thread and its messages.
     */
    delete: async (threadId: string): Promise<DeleteThreadResponse> => {
      const res = await fetch(`${BASE}/threads/${threadId}`, {
        method: "DELETE",
      });
      return handleResponse<DeleteThreadResponse>(res);
    },

    /**
     * GET /api/v1/threads/{thread_id}/messages — get full message history.
     */
    getMessages: async (threadId: string): Promise<ThreadMessagesResponse> => {
      const res = await fetch(`${BASE}/threads/${threadId}/messages`);
      return handleResponse<ThreadMessagesResponse>(res);
    },

    /**
     * Returns the URL for the SSE message stream endpoint.
     * POST /api/v1/threads/{thread_id}/messages — streams AI response via SSE.
     */
    getMessageStreamUrl: (threadId: string): string =>
      `${BASE}/threads/${threadId}/messages`,
  },
};
