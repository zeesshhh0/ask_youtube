"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { ChatHeader } from "./ChatHeader";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { apiClient } from "@/lib/api/client";
import {
  handleSSEStream,
  createStreamController,
} from "@/lib/api/streamHandler";
import { getErrorMessage } from "@/lib/errors";
import type { Message, Thread } from "@/lib/types";
import { toast } from "sonner";

interface ChatContainerProps {
  thread: Thread;
  initialMessages?: Message[];
}

export function ChatContainer({
  thread,
  initialMessages = [],
}: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(!initialMessages.length);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);
  const messageIdRef = useRef(
    Math.max(...initialMessages.map((m) => m.message_id), 0)
  );

  // Load chat history on mount
  useEffect(() => {
    if (initialMessages.length > 0) return;

    async function loadHistory() {
      try {
        const response = await apiClient.threads.getMessages(thread.thread_id);
        // Map backend role ("human"/"ai") to UI sender ("user"/"ai")
        const historyMessages = (response.messages || []).map((m) => ({
          message_id: m.message_id,
          sender: (m.role === "human" ? "user" : "ai") as "user" | "ai",
          content: m.content,
          metadata: m.metadata ?? undefined,
          created_at: m.created_at,
        }));
        setMessages(historyMessages);
        messageIdRef.current = Math.max(
          ...historyMessages.map((m) => m.message_id),
          0
        );
      } catch (error) {
        toast.error(getErrorMessage(error));
      } finally {
        setIsLoading(false);
      }
    }

    loadHistory();
  }, [thread.thread_id, initialMessages.length]);

  // Add welcome message if this is a new thread with no messages
  useEffect(() => {
    if (!isLoading && messages.length === 0 && thread.summary) {
      const welcomeMessage: Message = {
        message_id: 0,
        sender: "ai",
        content: `👋 Hi! I've processed the video "${thread.title}".\n\nHere's a quick summary:\n${thread.summary}\n\nFeel free to ask me anything about the content, concepts explained, or specific details from the video!`,
        created_at: new Date().toISOString(),
      };
      setMessages([welcomeMessage]);
    }
  }, [isLoading, messages?.length, thread.title, thread.summary]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      // Optimistic update - add user message immediately
      const userMessageId = ++messageIdRef.current;
      const userMessage: Message = {
        message_id: userMessageId,
        sender: "user",
        content,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setStreamingContent("");

      // Create abort controller for this request
      abortControllerRef.current = createStreamController();

      let aiContent = "";
      const aiMessageId = ++messageIdRef.current;

      try {
        await handleSSEStream(
          apiClient.threads.getMessageStreamUrl(thread.thread_id),
          { content },
          {
            onToken: (token) => {
              aiContent += token;
              setStreamingContent(aiContent);
            },
            onComplete: () => {
              const aiMessage: Message = {
                message_id: aiMessageId,
                sender: "ai",
                content: aiContent,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, aiMessage]);
              setIsStreaming(false);
              setStreamingContent("");
            },
            onError: (error) => {
              toast.error(getErrorMessage(error));
              setIsStreaming(false);
              setStreamingContent("");
            },
          },
          abortControllerRef.current.signal
        );
      } catch (error) {
        toast.error(getErrorMessage(error));
        setIsStreaming(false);
        setStreamingContent("");
      }
    },
    [thread.thread_id]
  );

  // Show streaming message in the list
  const displayMessages = isStreaming && streamingContent
    ? [
      ...messages,
      {
        message_id: -1,
        sender: "ai" as const,
        content: streamingContent,
        created_at: new Date().toISOString(),
      },
    ]
    : messages;

  return (
    <div className="flex flex-col h-full">
      <ChatHeader title={thread.title ?? undefined} videoId={thread.video_id} />

      <ChatMessages
        messages={displayMessages}
        isLoading={isLoading}
        isStreaming={isStreaming}
        streamingMessageId={isStreaming ? -1 : undefined}
      />

      <ChatInput
        onSubmit={handleSendMessage}
        disabled={isLoading || isStreaming}
      />
    </div>
  );
}
