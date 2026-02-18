"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { VideoUrlPrompt } from "@/components/chat/VideoUrlPrompt";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { useChatContext } from "@/components/providers/ChatProvider";
import { apiClient } from "@/lib/api/client";
import { getErrorMessage } from "@/lib/errors";
import type { Thread } from "@/lib/types";
import { toast } from "sonner";

export default function NewChatPage() {
  const router = useRouter();
  const { addThread, setActiveThread, setProcessing } = useChatContext();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (url: string) => {
      setIsLoading(true);
      setProcessing(true);
      setError(null);

      try {
        // POST /api/v1/threads — ingest video and create thread
        const response = await apiClient.threads.create(url);

        const thread: Thread = {
          thread_id: response.thread_id,
          video_id: response.video_id,
          title: response.title,
          summary: response.summary,
          created_at: new Date().toISOString(),
        };

        addThread(thread);
        setActiveThread(response.thread_id);

        // Navigate to the new thread
        router.push(`/chat/${response.thread_id}`);

        toast.success("Video processed successfully!");
      } catch (err) {
        const message = getErrorMessage(err);
        setError(message);
        toast.error(message);
      } finally {
        setIsLoading(false);
        setProcessing(false);
      }
    },
    [router, addThread, setActiveThread, setProcessing]
  );

  return (
    <div className="flex flex-col h-full">
      <ChatHeader />
      <VideoUrlPrompt
        onSubmit={handleSubmit}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}
