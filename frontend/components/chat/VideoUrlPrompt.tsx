"use client";

import { useState, useCallback, type FormEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { isValidYouTubeUrl } from "@/lib/config";
import { Youtube, ArrowRight, Loader2, AlertCircle } from "lucide-react";

interface VideoUrlPromptProps {
  onSubmit: (url: string) => Promise<void>;
  isLoading: boolean;
  error?: string | null;
}

const loadingMessages = [
  "Fetching transcript...",
  "Processing transcripts...",
  "Preparing chat...",
];

export function VideoUrlPrompt({
  onSubmit,
  isLoading,
  error,
}: VideoUrlPromptProps) {
  const [url, setUrl] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setValidationError(null);

      if (!url.trim()) {
        setValidationError("Please enter a YouTube URL");
        return;
      }

      if (!isValidYouTubeUrl(url)) {
        setValidationError(
          "Please enter a valid YouTube URL (e.g., https://www.youtube.com/watch?v=xxxxx)"
        );
        return;
      }

      // Start loading animation
      setLoadingStep(0);
      const interval = setInterval(() => {
        setLoadingStep((prev) =>
          prev < loadingMessages.length - 1 ? prev + 1 : prev
        );
      }, 2000);

      try {
        await onSubmit(url);
      } finally {
        clearInterval(interval);
      }
    },
    [url, onSubmit]
  );

  const displayError = error || validationError;

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="space-y-6 py-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>

            <div className="space-y-4">
              {loadingMessages.map((message, index) => (
                <div key={message} className="flex items-center gap-3">
                  {index < loadingStep ? (
                    <div className="h-4 w-4 rounded-full bg-green-500" />
                  ) : index === loadingStep ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  ) : (
                    <Skeleton className="h-4 w-4 rounded-full" />
                  )}
                  <span
                    className={
                      index <= loadingStep
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }
                  >
                    {message}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardContent className="space-y-6 py-8">
          {/* Header */}
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Youtube className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold">Chat with any YouTube video</h1>
            <p className="mt-2 text-muted-foreground">
              Paste a URL below to start asking questions about the video content
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setValidationError(null);
                }}
                className="h-12 text-base"
                aria-label="YouTube video URL"
                aria-invalid={!!displayError}
              />
              {displayError && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span>{displayError}</span>
                </div>
              )}
            </div>

            <Button
              type="submit"
              className="w-full h-12 text-base"
              disabled={!url.trim()}
            >
              Start Chat
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </form>

          {/* Hint */}
          <p className="text-center text-xs text-muted-foreground">
            Works best with videos that have english captions/transcripts available
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
