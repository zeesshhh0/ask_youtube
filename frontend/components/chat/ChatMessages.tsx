"use client";

import { useRef, useEffect } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { RefreshCcw } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { VideoCard } from "../video/VideoCard";
import { VideoSummary } from "../video/VideoSummary";
import type { Message } from "@/lib/types";

interface ChatMessagesProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  streamingMessageId?: number;
  videoInfo?: {
    videoId: string;
    title: string;
  };
  summary?: string | null;
  error?: string | null;
  onRetry?: () => void;
}

export function ChatMessages({
  messages,
  isLoading = false,
  isStreaming = false,
  streamingMessageId,
  videoInfo,
  summary,
  error,
  onRetry,
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages, isStreaming, error]);

  if (isLoading) {
    return (
      <div className="flex-1 p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-8 w-8 rounded-full shrink-0" />
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>No messages yet. Start the conversation!</p>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1 min-h-0" ref={scrollRef}>
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {(videoInfo || summary) && (
          <div className="mb-8 space-y-4">
            {videoInfo && (
              <VideoCard
                videoId={videoInfo.videoId}
                title={videoInfo.title}
              />
            )}
            {summary && <VideoSummary summary={summary} />}
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble
            key={message.message_id}
            message={message}
            isStreaming={
              isStreaming && message.message_id === streamingMessageId
            }
          />
        ))}

        {isStreaming && !streamingMessageId && <TypingIndicator />}

        {error && (
          <div className="flex flex-col items-center gap-2 py-4 animate-in fade-in slide-in-from-bottom-2">
            <p className="text-sm text-destructive font-medium">
              {error}
            </p>
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="gap-2"
              >
                <RefreshCcw className="h-4 w-4" />
                Retry
              </Button>
            )}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
