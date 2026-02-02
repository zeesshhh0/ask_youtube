"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { useChatContext } from "@/components/providers/ChatProvider";
import { apiClient } from "@/lib/api/client";
import { getErrorMessage } from "@/lib/errors";
import { Skeleton } from "@/components/ui/skeleton";
import type { Thread, Message } from "@/lib/types";
import { toast } from "sonner";

export default function ThreadPage() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;
  const { threads, setActiveThread, addThread } = useChatContext();

  const [thread, setThread] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setActiveThread(threadId);

    // Check if thread exists in context
    const existingThread = threads.find((t) => t.thread_id === threadId);

    if (existingThread) {
      setThread(existingThread);
      // Still need to load messages
      loadMessages();
    } else {
      // Load thread and messages from API
      loadThreadData();
    }

    async function loadMessages() {
      try {
        const response = await apiClient.chat.getHistory(threadId);
        setMessages(response.messages || []);
      } catch (error) {
        toast.error(getErrorMessage(error));
      } finally {
        setIsLoading(false);
      }
    }

    async function loadThreadData() {
      try {
        const response = await apiClient.chat.getHistory(threadId);

        // Create thread from history response
        const threadData: Thread = {
          thread_id: response.thread_id,
          video_id: response.video_id,
          title: `Video ${response.video_id}`, // May need to get title from another source
          summary: "",
          created_at: response.messages[0]?.created_at || new Date().toISOString(),
        };

        setThread(threadData);
        setMessages(response.messages || []);
        addThread(threadData);
      } catch (error) {
        toast.error(getErrorMessage(error));
        // Redirect back to chat if thread not found
        router.push("/chat");
      } finally {
        setIsLoading(false);
      }
    }

    return () => {
      // Cleanup - could stop streaming here if needed
    };
  }, [threadId, threads, setActiveThread, addThread, router]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="border-b p-4">
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="flex-1 p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Thread not found</p>
      </div>
    );
  }

  return <ChatContainer thread={thread} initialMessages={messages} />;
}
