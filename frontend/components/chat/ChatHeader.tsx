"use client";

import { Button } from "@/components/ui/button";
import { useChatContext } from "@/components/providers/ChatProvider";
import { Menu, Youtube } from "lucide-react";

interface ChatHeaderProps {
  title?: string;
  videoId?: string;
}

export function ChatHeader({ title, videoId }: ChatHeaderProps) {
  const { toggleSidebar } = useChatContext();

  return (
    <header className="flex h-14 items-center gap-3 border-b px-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shrink-0">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        className="shrink-0 md:hidden"
        aria-label="Toggle sidebar"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {title ? (
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Youtube className="h-5 w-5 text-red-500 shrink-0" />
          <h1 className="font-medium truncate">{title}</h1>
          {videoId && (
            <a
              href={`https://www.youtube.com/watch?v=${videoId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
            >
              Open ↗
            </a>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Youtube className="h-5 w-5 text-primary" />
          <h1 className="font-medium">New Chat</h1>
        </div>
      )}
    </header>
  );
}
