"use client";

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { config } from "@/lib/config";
import { cn } from "@/lib/utils";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSubmit: (message: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSubmit,
  disabled = false,
  placeholder = "Ask a question about the video...",
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const charCount = input.length;
  const isOverLimit = charCount > config.maxMessageLength;
  const canSubmit = input.trim().length > 0 && !isOverLimit && !disabled;

  // Auto-resize textarea and focus management
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 400)}px`;
    }
  }, [input]);

  // Auto-focus on mount
  useEffect(() => {
    if (!disabled && !isSubmitting) {
      textareaRef.current?.focus();
    }
  }, [disabled, isSubmitting]);

  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      if (!canSubmit || isSubmitting) return;

      const message = input.trim();
      setInput("");
      setIsSubmitting(true);

      try {
        await onSubmit(message);
      } finally {
        setIsSubmitting(false);
        // Reset textarea height and refocus
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
          // Small delay to ensure it focuses after React state updates enable the input
          setTimeout(() => {
            textareaRef.current?.focus();
          }, 0);
        }
      }
    },
    [input, canSubmit, isSubmitting, onSubmit]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Submit on Enter (without Shift)
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <form onSubmit={handleSubmit} className="border-t bg-background p-4">
      <div className="mx-auto max-w-3xl">
        <div className="relative flex items-end gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSubmitting}
            rows={2}
            className={cn(
              "min-h-[64px] max-h-[400px] resize-none pr-12 py-3 text-base md:text-sm rounded-xl shadow-sm",
              isOverLimit && "border-destructive focus-visible:ring-destructive"
            )}
            aria-label="Message input"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!canSubmit || isSubmitting}
            className="absolute right-3 bottom-3 h-8 w-8"
            aria-label="Send message"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Character count */}
        {charCount > config.maxMessageLength * 0.8 && (
          <div
            className={cn(
              "mt-1 text-xs text-right",
              isOverLimit ? "text-destructive" : "text-muted-foreground"
            )}
          >
            {charCount}/{config.maxMessageLength}
          </div>
        )}
      </div>
    </form>
  );
}
