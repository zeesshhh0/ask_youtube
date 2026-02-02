"use client";

import { memo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Thread } from "@/lib/types";
import { MessageSquare, Youtube } from "lucide-react";

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onSelect: () => void;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: "short" });
  } else {
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  }
}

function ThreadItemComponent({ thread, isActive, onSelect }: ThreadItemProps) {
  return (
    <Button
      variant={isActive ? "secondary" : "ghost"}
      className={cn(
        "w-full justify-start gap-2 h-auto py-2 px-3",
        isActive && "bg-accent"
      )}
      onClick={onSelect}
    >
      <Youtube className="h-4 w-4 shrink-0 text-red-500" />
      <div className="flex-1 min-w-0 text-left">
        <p className="truncate text-sm font-medium">{thread.title}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(thread.created_at)}
        </p>
      </div>
    </Button>
  );
}

export const ThreadItem = memo(ThreadItemComponent);
