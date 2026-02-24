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

    // Check if thread already exists in context (just navigated from new-chat flow)
    const existingThread = threads.find((t) => t.thread_id === threadId);

    if (existingThread) {
      setThread(existingThread);
      loadMessages();
    } else {
      loadThreadData();
    }

    async function loadMessages() {
      try {
        // GET /api/v1/threads/{threadId}/messages
        const response = await apiClient.threads.getMessages(threadId);
        const mapped: Message[] = (response.messages || []).map((m) => ({
          message_id: m.message_id,
          sender: (m.role === "human" ? "user" : "ai") as "user" | "ai",
          content: m.content,
          metadata: m.metadata ?? undefined,
          created_at: m.created_at,
        }));
        setMessages(mapped);
      } catch (error) {
        toast.error(getErrorMessage(error));
      } finally {
        setIsLoading(false);
      }
    }

    async function loadThreadData() {
      try {
        // 1. Fetch thread list to find our thread details (video_id, title)
        const threadsList = (await apiClient.threads.list());
        const existingThreadInList = threadsList.find((t) => t.thread_id === threadId);

        // 2. Fetch history
        const response = await apiClient.threads.getMessages(threadId);

        const threadData: Thread = {
          thread_id: threadId,
          video_id: existingThreadInList?.video_id || "",
          title: existingThreadInList?.title || null,
          summary: null, // summary is only available from POST /threads response (or first AI message)
          created_at: response.messages[0]?.created_at || new Date().toISOString(),
        };

        setThread(threadData);

        const mapped: Message[] = (response.messages || []).map((m) => ({
          message_id: m.message_id,
          sender: (m.role === "human" ? "user" : "ai") as "user" | "ai",
          content: m.content,
          metadata: m.metadata ?? undefined,
          created_at: m.created_at,
        }));
        setMessages(mapped);
        addThread(threadData);
      } catch (error) {
        toast.error(getErrorMessage(error));
        router.push("/chat");
      } finally {
        setIsLoading(false);
      }
    }

    return () => {
      // Cleanup (e.g., abort streaming) can be added here
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col min-h-0">
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
      <div className="flex-1 flex flex-col min-h-0 items-center justify-center">
        <p className="text-muted-foreground">Thread not found</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <ChatContainer
        key={thread.thread_id}
        thread={thread}
        initialMessages={messages}
      />
    </div>
  );
}
