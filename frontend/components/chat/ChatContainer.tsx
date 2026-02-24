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
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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
        message_id: "welcome-message",
        sender: "ai",
        content: `👋 Hi! I've processed the video "${thread.title}". Feel free to ask me anything about the content, concepts explained, or specific details from the video!`,
        created_at: new Date().toISOString(),
      };
      setMessages([welcomeMessage]);
    }
  }, [isLoading, messages.length, thread.title, thread.summary]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      // Optimistic update - add user message immediately
      const userMessageId = crypto.randomUUID();
      const userMessage: Message = {
        message_id: userMessageId,
        sender: "user",
        content,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setStreamingContent("");
      setError(null);

      // Create abort controller for this request
      abortControllerRef.current = createStreamController();

      let aiContent = "";
      const aiMessageId = crypto.randomUUID();

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
              setIsStreaming(false);
              setStreamingContent("");

              if (aiContent.trim()) {
                const aiMessage: Message = {
                  message_id: aiMessageId,
                  sender: "ai",
                  content: aiContent,
                  created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, aiMessage]);
              }
            },
            onError: (err) => {
              const errorMessage = getErrorMessage(err);
              toast.error(errorMessage);
              setError(errorMessage);
              setIsStreaming(false);
            },
          },
          abortControllerRef.current.signal
        );
      } catch (err) {
        const errorMessage = getErrorMessage(err);
        toast.error(errorMessage);
        setError(errorMessage);
        setIsStreaming(false);
      }
    },
    [thread.thread_id]
  );

  const handleRetry = useCallback(() => {
    // Find last user message
    const lastUserMessage = [...messages].reverse().find((m) => m.sender === "user");
    if (lastUserMessage) {
      // Remove messages after that user message
      const index = messages.lastIndexOf(lastUserMessage);
      setMessages(messages.slice(0, index + 1));
      handleSendMessage(lastUserMessage.content);
    }
  }, [messages, handleSendMessage]);

  // Show streaming message in the list
  const displayMessages = (isStreaming || error) && streamingContent
    ? [
      ...messages,
      {
        message_id: "streaming-message",
        sender: "ai" as const,
        content: streamingContent,
        created_at: new Date().toISOString(),
        metadata: error ? { error: true } : undefined,
      },
    ]
    : messages;

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <ChatHeader title={thread.title ?? undefined} videoId={thread.video_id} />

      <ChatMessages
        messages={displayMessages}
        isLoading={isLoading}
        isStreaming={isStreaming}
        streamingMessageId={isStreaming && streamingContent ? "streaming-message" : undefined}
        videoInfo={
          thread.title
            ? { videoId: thread.video_id, title: thread.title }
            : undefined
        }
        summary={thread.summary}
        error={error}
        onRetry={handleRetry}
      />

      <ChatInput
        onSubmit={handleSendMessage}
        disabled={isLoading || isStreaming}
      />
    </div>
  );
}
