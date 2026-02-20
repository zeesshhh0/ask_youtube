"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  showAvatar?: boolean;
}

function formatTimestamp(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function MessageBubbleComponent({
  message,
  isStreaming = false,
  showAvatar = true,
}: MessageBubbleProps) {
  const isUser = message.sender === "user";
  const isError = message.metadata?.error === true;

  return (
    <div
      className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      {showAvatar && (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback
            className={cn(
              isUser
                ? "bg-primary text-primary-foreground"
                : isError
                  ? "bg-destructive text-destructive-foreground"
                  : "bg-muted text-muted-foreground"
            )}
          >
            {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
      )}

      {/* Message bubble */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                "max-w-[80%] rounded-2xl px-4 py-2",
                isUser
                  ? "rounded-tr-sm bg-primary text-primary-foreground"
                  : isError
                    ? "rounded-tl-sm bg-destructive/10 border border-destructive/20 text-destructive"
                    : "rounded-tl-sm bg-muted text-foreground"
              )}
            >
              {isUser ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
                  )}

                  {/* Citations */}
                  {message.metadata?.citations && Array.isArray(message.metadata.citations) && (
                    <div className="mt-4 pt-2 border-t border-muted-foreground/20">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                        Sources
                      </p>
                      <ul className="list-none p-0 m-0 space-y-1">
                        {(message.metadata.citations as any[]).map((citation, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex gap-2">
                            <span className="font-medium">[{i + 1}]</span>
                            <span>{citation.text || citation}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side={isUser ? "left" : "right"}>
            <p>{formatTimestamp(message.created_at)}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

export const MessageBubble = memo(MessageBubbleComponent);
