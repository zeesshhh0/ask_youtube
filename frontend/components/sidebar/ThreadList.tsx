"use client";

import { useRouter } from "next/navigation";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThreadItem } from "./ThreadItem";
import type { Thread } from "@/lib/types";

interface ThreadListProps {
  threads: Thread[];
  activeThreadId: string | null;
  onClose?: () => void;
}

export function ThreadList({
  threads,
  activeThreadId,
  onClose,
}: ThreadListProps) {
  const router = useRouter();

  if (threads.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-muted-foreground text-center">
          No chat history yet.
          <br />
          Start a new chat to get going!
        </p>
      </div>
    );
  }

  const handleSelect = (threadId: string) => {
    router.push(`/chat/${threadId}`);
    onClose?.();
  };

  return (
    <ScrollArea className="flex-1">
      <div className="p-2 space-y-1">
        {threads.map((thread) => (
          <ThreadItem
            key={thread.thread_id}
            thread={thread}
            isActive={thread.thread_id === activeThreadId}
            onSelect={() => handleSelect(thread.thread_id)}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
