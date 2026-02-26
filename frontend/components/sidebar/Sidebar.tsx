"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { useChatContext } from "@/components/providers/ChatProvider";
import { NewChatButton } from "./NewChatButton";
import { ThreadList } from "./ThreadList";

export function Sidebar() {
  const { threads, activeThreadId, isSidebarOpen, toggleSidebar } =
    useChatContext();

  return (
    <>
      {/* Mobile sidebar (Sheet) */}
      <Sheet open={isSidebarOpen} onOpenChange={toggleSidebar}>
        <SheetContent side="left" className="w-[280px] p-0 flex flex-col">
          <SheetHeader className="p-4 pb-0">
            <SheetTitle className="text-left">Ask Youtube</SheetTitle>
          </SheetHeader>

          <div className="p-4">
            <NewChatButton />
          </div>

          <Separator />

          <ThreadList
            threads={threads}
            activeThreadId={activeThreadId}
            onClose={toggleSidebar}
          />
        </SheetContent>
      </Sheet>

      {/* Desktop sidebar (persistent) */}
      <aside className="hidden md:flex w-[280px] border-r flex-col bg-muted/30">
        <div className="flex h-14 items-center px-4 border-b">
          <h1 className="font-semibold text-lg">Ask Youtube</h1>
        </div>

        <div className="p-4">
          <NewChatButton />
        </div>

        <Separator />

        <ThreadList threads={threads} activeThreadId={activeThreadId} />
      </aside>
    </>
  );
}
