import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import type { InitResponse, HistoryResponse, Thread } from "@/lib/types";

const API_BASE_URL = config.apiUrl;

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
  chat: {
    /**
     * Initialize a new chat thread with a YouTube video
     */
    init: async (youtubeUrl: string): Promise<InitResponse> => {
      const res = await fetch(`${API_BASE_URL}/chat/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: youtubeUrl }),
      });
      return handleResponse<InitResponse>(res);
    },

    /**
     * Get chat history for a thread
     */
    getHistory: async (threadId: string): Promise<HistoryResponse> => {
      const res = await fetch(`${API_BASE_URL}/chat/${threadId}/history`);
      return handleResponse<HistoryResponse>(res);
    },

    /**
     * Get all chat threads (if backend supports it)
     */
    getThreads: async (): Promise<Thread[]> => {
      try {
        const res = await fetch(`${API_BASE_URL}/chat/threads`);
        return handleResponse<Thread[]>(res);
      } catch {
        // If endpoint doesn't exist, return empty array
        return [];
      }
    },

    /**
     * Delete a chat thread
     */
    deleteThread: async (threadId: string): Promise<void> => {
      const res = await fetch(`${API_BASE_URL}/chat/${threadId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        throw new ApiError("Failed to delete thread", res.status);
      }
    },

    /**
     * Get the streaming message endpoint URL
     */
    getMessageStreamUrl: (threadId: string): string => {
      return `${API_BASE_URL}/chat/${threadId}/message`;
    },
  },
};
