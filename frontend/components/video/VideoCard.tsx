"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Youtube, ExternalLink } from "lucide-react";

interface VideoCardProps {
  videoId: string;
  title: string;
  channel?: string;
  duration?: string;
}

export function VideoCard({ videoId, title, channel, duration }: VideoCardProps) {
  const thumbnailUrl = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
  const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;

  return (
    <Card className="overflow-hidden">
      <div className="relative">
        <img
          src={thumbnailUrl}
          alt={title}
          className="w-full aspect-video object-cover"
        />
        {duration && (
          <Badge
            variant="secondary"
            className="absolute bottom-2 right-2 bg-black/80 text-white"
          >
            {duration}
          </Badge>
        )}
      </div>
      <CardContent className="p-3">
        <h3 className="font-medium line-clamp-2 text-sm">{title}</h3>
        {channel && (
          <p className="text-xs text-muted-foreground mt-1">{channel}</p>
        )}
        <a
          href={videoUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-2"
        >
          <Youtube className="h-3 w-3" />
          Watch on YouTube
          <ExternalLink className="h-3 w-3" />
        </a>
      </CardContent>
    </Card>
  );
}
