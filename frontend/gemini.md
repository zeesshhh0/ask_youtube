# Ask Youtube Frontend Agent Specification

## 1. Project Overview

**Name:** Ask Youtube UI  
**Type:** Educational Chat Interface for YouTube Videos  
**Framework:** Next.js 14+ (App Router)  
**Goal:** Create a "Chat with Video" interface where users can interact with educational YouTube content through an AI-powered conversational experience.  
**Status:** Proof of Concept (PoC)  
**Design Philosophy:** Minimalist, clean, and focused on the conversation experience.

---

## 2. Tech Stack

### Core Framework

- **Framework:** Next.js 14+ with App Router
- **Language:** TypeScript
- **Runtime:** Node.js 18+
- **Package Manager:** pnpm (recommended) or npm

### UI & Styling

- **CSS Framework:** Tailwind CSS 3.x
- **Component Library:** shadcn/ui
  - `Sheet` - Sidebar drawer
  - `Button` - All button interactions
  - `Input` - Form inputs
  - `ScrollArea` - Scrollable containers
  - `Card` - Content containers
  - `Skeleton` - Loading states
  - `Avatar` - Message sender indicators
  - `Separator` - Visual dividers
  - `Badge` - Status indicators

### AI Integration

- **SDK:** Vercel AI SDK (`ai` package)
- **Primary Hook:** `useChat` for streaming responses
- **Backend Integration:** REST API with Server-Sent Events (SSE)

### State Management

- **Local State:** React hooks (`useState`, `useReducer`)
- **Server State:** Vercel AI SDK built-in state
- **Persistence:** Browser storage for UI preferences (NOT localStorage - see constraints)

### Data Fetching

- **Client:** Native `fetch` API
- **Server Components:** Direct async/await with fetch
- **Streaming:** EventSource API for SSE

---

## 3. Application Architecture

### Route Structure

```
app/
├── layout.tsx                 # Root layout with providers
├── page.tsx                   # Landing/redirect to /chat
├── chat/
│   ├── layout.tsx            # Chat layout with sidebar
│   ├── page.tsx              # Empty state (new chat)
│   └── [threadId]/
│       └── page.tsx          # Active chat thread
├── api/
│   └── chat/
│       └── route.ts          # Proxy to backend API
└── globals.css               # Tailwind + custom styles
```

### Component Structure

```
components/
├── chat/
│   ├── ChatContainer.tsx          # Main chat layout
│   ├── ChatHeader.tsx             # Video info header
│   ├── ChatMessages.tsx           # Message list with auto-scroll
│   ├── ChatInput.tsx              # Message input area
│   ├── MessageBubble.tsx          # Individual message component
│   ├── TypingIndicator.tsx        # AI typing animation
│   └── VideoUrlPrompt.tsx         # Initial URL input state
├── sidebar/
│   ├── Sidebar.tsx                # Main drawer component
│   ├── ThreadList.tsx             # List of chat threads
│   ├── ThreadItem.tsx             # Individual thread item
│   └── NewChatButton.tsx          # New chat action
├── video/
│   ├── VideoCard.tsx              # Video metadata display
│   └── VideoSummary.tsx           # AI-generated summary
├── ui/
│   └── [shadcn components]        # From shadcn/ui
└── providers/
    └── ChatProvider.tsx           # Global chat state context
```

---

## 4. User Flows

### Flow 1: New Chat Initialization

```
1. User lands on /chat
   ├─> Display VideoUrlPrompt (centered, empty state)
   └─> Show "New Chat" CTA

2. User enters YouTube URL and submits
   ├─> Show loading state (skeleton + progress message)
   ├─> Call POST /api/v1/threads
   └─> Backend processes:
       ├─> Fetch transcript
       ├─> Generate embeddings
       ├─> Create vector DB collection
       └─> Generate summary

3. On success:
   ├─> Redirect to /chat/[threadId]
   ├─> Display VideoCard with metadata
   ├─> Show AI welcome message with summary
   ├─> Add thread to sidebar
   └─> Enable chat input

4. On error:
   ├─> Show error toast
   ├─> Display helpful error message
   └─> Allow retry
```

### Flow 2: Continuing Conversation

```
1. User on /chat/[threadId]
   ├─> Load chat history from GET /api/v1/threads/{threadId}/messages
   ├─> Display messages with proper sender attribution
   └─> Auto-scroll to latest message

2. User types message and submits
   ├─> Disable input (prevent double-submit)
   ├─> Add user message to UI immediately
   ├─> Show typing indicator
   └─> Call POST /api/v1/threads/{threadId}/messages (SSE stream)

3. Stream AI response
   ├─> Append tokens to message bubble in real-time
   ├─> Update scroll position
   └─> Show source citations (if available)

4. On stream complete:
   ├─> Enable input
   ├─> Update message in history
   └─> Clear typing indicator

5. On error:
   ├─> Show error message in chat
   ├─> Re-enable input
   └─> Allow retry
```

### Flow 3: Thread Management

```
1. View thread list in sidebar
   ├─> Display recent threads (sorted by created_at DESC)
   ├─> Show video thumbnail + title
   └─> Highlight active thread

2. Switch threads
   ├─> Click thread item
   ├─> Navigate to /chat/[threadId]
   ├─> Load thread history
   └─> Update active state

3. Create new chat
   ├─> Click "New Chat" button
   ├─> Navigate to /chat
   └─> Reset to empty state

4. Delete thread (future)
   ├─> Show confirmation dialog
   ├─> Call DELETE /api/v1/threads/{threadId}
   ├─> Remove from sidebar
   └─> Redirect to /chat if active
```

---

## 5. State Management

### Global State (React Context)

```typescript
// context/ChatContext.tsx
interface ChatContextState {
  // Thread Management
  threads: Thread[];
  activeThreadId: string | null;

  // UI State
  isSidebarOpen: boolean;
  isProcessing: boolean;

  // Actions
  setActiveThread: (threadId: string) => void;
  addThread: (thread: Thread) => void;
  removeThread: (threadId: string) => void;
  toggleSidebar: () => void;
}
```

### Local Component State

```typescript
// components/chat/ChatContainer.tsx
interface ChatState {
  // Message History
  messages: Message[];

  // Input State
  inputValue: string;
  isSubmitting: boolean;

  // Streaming State
  streamingMessage: string;
  isStreaming: boolean;

  // Error Handling
  error: string | null;
}
```

### Vercel AI SDK Integration

```typescript
// Using useChat hook
import { useChat } from "ai/react";

const {
  messages, // Chat history
  input, // Input field value
  handleInputChange,
  handleSubmit,
  isLoading, // Streaming state
  error,
  reload, // Retry last message
  stop, // Stop streaming
} = useChat({
  api: `/api/v1/threads/${threadId}/messages`,
  streamMode: "text",
  onFinish: (message) => {
    // Save to history, update UI
  },
  onError: (error) => {
    // Handle errors
  },
});
```

---

## 6. API Integration Layer

> **Base URL:** `http://localhost:8000/api/v1` (configured via `NEXT_PUBLIC_API_URL`)

### Endpoints Reference

| Method   | Path                            | Description                             |
| -------- | ------------------------------- | --------------------------------------- |
| `POST`   | `/threads`                      | Create thread & ingest YouTube video    |
| `GET`    | `/threads`                      | List all threads                        |
| `DELETE` | `/threads/{thread_id}`          | Delete a thread and its messages        |
| `POST`   | `/threads/{thread_id}/messages` | Send a message — **returns SSE stream** |
| `GET`    | `/threads/{thread_id}/messages` | Get full message history                |

---

### Request & Response Schemas

#### `POST /threads` — Create Thread

**Request body:**

```json
{ "video_url": "https://www.youtube.com/watch?v=..." }
```

**Response:**

```json
{
  "thread_id": "uuid-here",
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "summary": "AI-generated global summary..."
}
```

#### `GET /threads` — List Threads

**Response:**

```json
[
  {
    "thread_id": "6e0e092e-94f5-49cd-9202-8b43106f015a",
    "title": "Video Title",
    "video_id": "dQw4w9WgXcQ",
    "created_at": "2026-01-31T11:02:43.793765"
  }
]
```

#### `DELETE /threads/{thread_id}` — Delete Thread

**Response:**

```json
{ "success": true, "thread_id": "uuid-here" }
```

#### `POST /threads/{thread_id}/messages` — Send Message (SSE)

**Request body:**

```json
{ "content": "What is this video about?" }
```

**Response:** `Content-Type: text/event-stream` — see [SSE Streaming](#sse-streaming) below.

#### `GET /threads/{thread_id}/messages` — Get History

**Response:**

```json
{
  "thread_id": "uuid-here",
  "messages": [
    {
      "message_id": 0,
      "role": "human",
      "content": "What is this video about?",
      "metadata": null,
      "created_at": "2026-01-31T11:02:43.793765"
    },
    {
      "message_id": 1,
      "role": "ai",
      "content": "This video covers...",
      "metadata": { "model": "gemini-2.5-flash" },
      "created_at": "2026-01-31T11:02:45.123456"
    }
  ]
}
```

> **Note:** `role` is `"human"` or `"ai"` (not `"user"`). `message_id` is the 0-based index of the message in the LangGraph state, not a DB primary key.

---

### SSE Streaming

The `POST /threads/{thread_id}/messages` endpoint streams the AI response as [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). Each event is a JSON-encoded object on the `data:` field.

#### SSE Event Types

| `type`  | When emitted               | Payload fields    |
| ------- | -------------------------- | ----------------- |
| `token` | For every LLM output chunk | `content: string` |
| `end`   | After the last token       | _(none)_          |

**Wire format example:**

```
data: {"type": "token", "content": "This "}

data: {"type": "token", "content": "video "}

data: {"type": "token", "content": "covers..."}

data: {"type": "end"}

```

> **Important:** `EventSource` does not support `POST` requests natively. Use `fetch` with `ReadableStream` to consume the SSE response from a POST body.

---

### Base API Client

```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE = `${API_BASE_URL}/api/v1`;

export const apiClient = {
  threads: {
    /** POST /threads — ingest a YouTube video and create a thread */
    create: async (videoUrl: string) => {
      const res = await fetch(`${BASE}/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl }),
      });
      if (!res.ok) throw new Error("Failed to initialize chat");
      return res.json() as Promise<CreateThreadResponse>;
    },

    /** GET /threads — list all threads */
    list: async () => {
      const res = await fetch(`${BASE}/threads`);
      if (!res.ok) throw new Error("Failed to fetch threads");
      return res.json() as Promise<ThreadListItem[]>;
    },

    /** DELETE /threads/{thread_id} */
    delete: async (threadId: string) => {
      const res = await fetch(`${BASE}/threads/${threadId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete thread");
      return res.json() as Promise<DeleteThreadResponse>;
    },

    /** GET /threads/{thread_id}/messages — full history */
    getMessages: async (threadId: string) => {
      const res = await fetch(`${BASE}/threads/${threadId}/messages`);
      if (!res.ok) throw new Error("Failed to fetch history");
      return res.json() as Promise<ThreadMessagesResponse>;
    },

    /**
     * POST /threads/{thread_id}/messages — send a message.
     * Returns a raw Response whose body is an SSE stream.
     * Use handleSSEStream() to consume it.
     */
    sendMessage: (threadId: string, content: string) =>
      fetch(`${BASE}/threads/${threadId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }),
  },
};
```

### TypeScript Types (matching backend schemas)

```typescript
// lib/api/types.ts

export interface CreateThreadResponse {
  thread_id: string;
  video_id: string;
  title: string | null;
  summary: string | null;
}

export interface ThreadListItem {
  thread_id: string;
  title: string | null;
  video_id: string;
  created_at: string; // ISO 8601
}

export interface MessageResponse {
  message_id: number; // 0-based index in LangGraph state
  role: "human" | "ai";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string; // ISO 8601
}

export interface ThreadMessagesResponse {
  thread_id: string;
  messages: MessageResponse[];
}

export interface DeleteThreadResponse {
  success: boolean;
  thread_id: string;
}

// SSE event shapes (data field of each SSE event)
export type SSEEvent =
  | { type: "token"; content: string } // partial AI response chunk
  | { type: "end" }; // stream finished
```

### SSE Stream Handler

> **Why `fetch` instead of `EventSource`?**  
> The native `EventSource` API only supports `GET` requests. Since the message endpoint is `POST`, we use `fetch` with a `ReadableStream` reader to consume the SSE response.

```typescript
// lib/api/streamHandler.ts

import type { SSEEvent } from "./types";

/**
 * Sends a message to the backend and streams the AI response via SSE.
 *
 * @param threadId  - The active thread ID
 * @param content   - The user's message text
 * @param onToken   - Called for each streamed token chunk
 * @param onComplete - Called when the stream ends (type: "end" received)
 * @param onError   - Called on network or parse errors
 * @returns Cleanup function that aborts the fetch if called
 */
export function handleSSEStream(
  threadId: string,
  content: string,
  onToken: (token: string) => void,
  onComplete: () => void,
  onError: (error: Error) => void,
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`/api/v1/threads/${threadId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += value;
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? ""; // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json) continue;

          const event: SSEEvent = JSON.parse(json);

          if (event.type === "token") {
            onToken(event.content);
          } else if (event.type === "end") {
            onComplete();
            return;
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  })();

  return () => controller.abort(); // cleanup / cancel stream
}
```

---

## 7. Component Specifications

### 7.1 ChatContainer

**Purpose:** Main container orchestrating the chat experience  
**Location:** `components/chat/ChatContainer.tsx`

```typescript
interface ChatContainerProps {
  threadId?: string;
  initialMessages?: Message[];
}

// Key Features:
// - Auto-scroll to bottom on new messages
// - Handle streaming responses
// - Manage message history
// - Coordinate with ChatInput and ChatMessages
```

**Layout:**

```
┌─────────────────────────────────────────┐
│ ChatHeader (video info)                 │
├─────────────────────────────────────────┤
│                                         │
│                                         │
│ ChatMessages (scrollable)               │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ ChatInput (fixed bottom)                │
└─────────────────────────────────────────┘
```

### 7.2 VideoUrlPrompt

**Purpose:** Initial state for new chat  
**Location:** `components/chat/VideoUrlPrompt.tsx`

```typescript
interface VideoUrlPromptProps {
  onSubmit: (url: string) => Promise<void>;
  isLoading: boolean;
}

// Key Features:
// - URL validation (YouTube format)
// - Loading states with skeleton
// - Error handling with helpful messages
// - Example URLs for demo
```

**UI States:**

1. **Empty:** Input field + CTA
2. **Loading:** Skeleton + progress messages
   - "Fetching transcript..."
   - "Generating embeddings..."
   - "Preparing chat..."
3. **Error:** Error message + retry button

### 7.3 MessageBubble

**Purpose:** Display individual chat messages  
**Location:** `components/chat/MessageBubble.tsx`

```typescript
interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  showAvatar?: boolean;
}

// Message Types:
// - user: Right-aligned, accent color
// - ai: Left-aligned, muted color
// - system: Centered, small text (e.g., "Chat created")

// Key Features:
// - Markdown rendering for AI responses
// - Code syntax highlighting
// - Timestamp on hover
// - Source citations (if available)
```

**Styling:**

```css
/* User Message */
.message-user {
  @apply ml-auto max-w-[80%] rounded-2xl rounded-tr-sm 
         bg-blue-600 text-white px-4 py-2;
}

/* AI Message */
.message-ai {
  @apply mr-auto max-w-[80%] rounded-2xl rounded-tl-sm 
         bg-gray-100 dark:bg-gray-800 px-4 py-2;
}

/* Streaming Cursor */
.streaming-cursor {
  @apply inline-block w-2 h-4 bg-current animate-pulse;
}
```

### 7.4 Sidebar

**Purpose:** Thread navigation and management  
**Location:** `components/sidebar/Sidebar.tsx`

```typescript
interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  onThreadSelect: (threadId: string) => void;
  onNewChat: () => void;
}

// shadcn/ui Sheet Configuration:
// - Side: "left"
// - Size: "sm" (280px)
// - Close on thread select (mobile)
// - Persistent on desktop
```

**Layout:**

```
┌─────────────────────┐
│ [New Chat] Button   │
├─────────────────────┤
│ ThreadList          │
│ ├─ Thread 1         │
│ ├─ Thread 2 (active)│
│ └─ Thread 3         │
│                     │
│ (scroll if needed)  │
└─────────────────────┘
```

### 7.5 ChatInput

**Purpose:** Message composition area  
**Location:** `components/chat/ChatInput.tsx`

```typescript
interface ChatInputProps {
  onSubmit: (message: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}

// Key Features:
// - Auto-resize textarea
// - Enter to submit, Shift+Enter for newline
// - Character count (optional)
// - Disabled state during streaming
// - Submit button with loading state
```

**Accessibility:**

```typescript
<form onSubmit={handleSubmit}>
  <Textarea
    aria-label="Chat message"
    placeholder="Ask about the video..."
    disabled={disabled}
    onKeyDown={handleKeyDown}
  />
  <Button
    type="submit"
    disabled={disabled || !value.trim()}
    aria-label="Send message"
  >
    {isLoading ? <Loader2 className="animate-spin" /> : <Send />}
  </Button>
</form>
```

---

## 8. Styling & Design System

### Color Palette

```css
/* Light Mode */
--background: 0 0% 100%;
--foreground: 222.2 84% 4.9%;
--card: 0 0% 100%;
--card-foreground: 222.2 84% 4.9%;
--primary: 221.2 83.2% 53.3%; /* Blue for user messages */
--primary-foreground: 210 40% 98%;
--muted: 210 40% 96.1%; /* AI message background */
--muted-foreground: 215.4 16.3% 46.9%;

/* Dark Mode */
--background: 222.2 84% 4.9%;
--foreground: 210 40% 98%;
--card: 222.2 84% 4.9%;
--card-foreground: 210 40% 98%;
--primary: 217.2 91.2% 59.8%;
--primary-foreground: 222.2 47.4% 11.2%;
--muted: 217.2 32.6% 17.5%;
--muted-foreground: 215 20.2% 65.1%;
```

### Typography

```css
/* Font Stack */
font-family:
  "Inter",
  system-ui,
  -apple-system,
  "Segoe UI",
  sans-serif;

/* Scale */
--text-xs: 0.75rem; /* Timestamps, metadata */
--text-sm: 0.875rem; /* Secondary text */
--text-base: 1rem; /* Body text, messages */
--text-lg: 1.125rem; /* Headings */
--text-xl: 1.25rem; /* Page titles */
```

### Spacing System

```css
/* Consistent spacing for chat UI */
--chat-padding: 1rem; /* Message padding */
--chat-gap: 0.75rem; /* Gap between messages */
--chat-input-height: 3.5rem; /* Input area height */
--sidebar-width: 280px; /* Sidebar width */
```

### Responsive Breakpoints

```typescript
// Tailwind config
const breakpoints = {
  sm: "640px", // Mobile landscape
  md: "768px", // Tablet
  lg: "1024px", // Desktop
  xl: "1280px", // Large desktop
};

// Sidebar behavior:
// - Mobile (< md): Sheet overlay
// - Desktop (>= md): Persistent sidebar
```

---

## 9. Performance Optimizations

### Code Splitting

```typescript
// Lazy load heavy components
const VideoPlayer = dynamic(() => import('@/components/video/VideoPlayer'), {
  loading: () => <Skeleton className="aspect-video" />,
  ssr: false,
});

const MarkdownRenderer = dynamic(() => import('@/components/MarkdownRenderer'), {
  loading: () => <div>Loading...</div>,
});
```

### Message Virtualization

```typescript
// For threads with 100+ messages
import { useVirtualizer } from '@tanstack/react-virtual';

function ChatMessages({ messages }) {
  const parentRef = useRef(null);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80, // Estimated message height
    overscan: 5,
  });

  return (
    <ScrollArea ref={parentRef}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((item) => (
          <MessageBubble
            key={item.key}
            message={messages[item.index]}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${item.start}px)`,
            }}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
```

### Optimistic Updates

```typescript
// Add user message immediately
function handleSubmit(content: string) {
  const optimisticMessage: Message = {
    message_id: Date.now(), // Temporary ID
    sender: "user",
    content,
    created_at: new Date().toISOString(),
  };

  setMessages((prev) => [...prev, optimisticMessage]);

  // Then send to backend
  sendMessage(content).catch(() => {
    // Rollback on error
    setMessages((prev) =>
      prev.filter((m) => m.message_id !== optimisticMessage.message_id),
    );
  });
}
```

### Image Optimization

```typescript
// Use Next.js Image for thumbnails
import Image from 'next/image';

<Image
  src={video.thumbnail_url}
  alt={video.title}
  width={320}
  height={180}
  className="rounded-lg"
  loading="lazy"
  placeholder="blur"
  blurDataURL="data:image/jpeg;base64,..."
/>
```

---

## 10. Accessibility (a11y)

### Keyboard Navigation

```typescript
// Essential keyboard shortcuts
const shortcuts = {
  "Ctrl/Cmd + K": "Focus search",
  "Ctrl/Cmd + N": "New chat",
  Escape: "Close sidebar/modal",
  "ArrowUp/Down": "Navigate threads",
  Enter: "Select thread / Submit message",
  "Shift + Enter": "New line in input",
};
```

### ARIA Labels

```typescript
// Screen reader support
<nav aria-label="Chat threads">
  <ul role="list">
    {threads.map((thread) => (
      <li key={thread.thread_id}>
        <button
          role="link"
          aria-current={thread.thread_id === activeThreadId ? 'page' : undefined}
          aria-label={`Chat about ${thread.title}`}
        >
          {thread.title}
        </button>
      </li>
    ))}
  </ul>
</nav>

<div role="log" aria-live="polite" aria-atomic="false">
  {/* Chat messages - announce new messages */}
</div>

<form aria-label="Send message">
  <label htmlFor="message-input" className="sr-only">
    Type your message
  </label>
  <textarea id="message-input" />
</form>
```

### Focus Management

```typescript
// Focus input after thread switch
useEffect(() => {
  if (inputRef.current && !isLoading) {
    inputRef.current.focus();
  }
}, [threadId, isLoading]);

// Trap focus in modal
import { FocusTrap } from '@headlessui/react';

<FocusTrap>
  <Sheet>
    {/* Sidebar content */}
  </Sheet>
</FocusTrap>
```

---

## 11. Error Handling

### Error Boundaries

```typescript
// app/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

### API Error Handling

```typescript
// lib/errors.ts
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Error mapping
const errorMessages: Record<number, string> = {
  400: "Invalid YouTube URL. Please check and try again.",
  404: "Chat thread not found.",
  429: "Too many requests. Please wait a moment.",
  500: "Server error. Please try again later.",
  503: "Service temporarily unavailable.",
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return errorMessages[error.status] || error.message;
  }
  return "An unexpected error occurred.";
}
```

### Toast Notifications

```typescript
// Using shadcn/ui toast
import { useToast } from '@/components/ui/use-toast';

const { toast } = useToast();

// Success toast
toast({
  title: 'Chat created!',
  description: 'You can now ask questions about the video.',
});

// Error toast
toast({
  variant: 'destructive',
  title: 'Failed to process video',
  description: getErrorMessage(error),
  action: <Button onClick={retry}>Retry</Button>,
});
```

---

## 12. Testing Strategy

### Component Testing (Jest + React Testing Library)

```typescript
// __tests__/components/MessageBubble.test.tsx
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '@/components/chat/MessageBubble';

describe('MessageBubble', () => {
  it('renders user message with correct styling', () => {
    const message = {
      message_id: 1,
      sender: 'user',
      content: 'Test message',
      created_at: '2024-01-27T10:00:00Z',
    };

    render(<MessageBubble message={message} />);

    const bubble = screen.getByText('Test message');
    expect(bubble).toHaveClass('message-user');
  });

  it('shows streaming cursor for AI message', () => {
    const message = {
      message_id: 2,
      sender: 'ai',
      content: 'Typing...',
      created_at: '2024-01-27T10:00:05Z',
    };

    render(<MessageBubble message={message} isStreaming />);

    expect(screen.getByTestId('streaming-cursor')).toBeInTheDocument();
  });
});
```

### Integration Testing (Playwright)

```typescript
// e2e/chat-flow.spec.ts
import { test, expect } from "@playwright/test";

test("complete chat initialization flow", async ({ page }) => {
  await page.goto("/chat");

  // Step 1: Enter YouTube URL
  await page.fill(
    'input[placeholder*="YouTube URL"]',
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  );
  await page.click('button:has-text("Start Chat")');

  // Step 2: Wait for processing
  await expect(page.locator("text=Fetching transcript")).toBeVisible();

  // Step 3: Verify chat is ready
  await expect(page).toHaveURL(/\/chat\/[a-z0-9-]+/);
  await expect(
    page.locator('role=textbox[name="Type your message"]'),
  ).toBeEnabled();

  // Step 4: Send message
  await page.fill(
    'role=textbox[name="Type your message"]',
    "What is this video about?",
  );
  await page.click('button[aria-label="Send message"]');

  // Step 5: Verify AI response
  await expect(page.locator(".message-ai").first()).toBeVisible({
    timeout: 10000,
  });
});
```

---

## 13. Environment Configuration

### Environment Variables

```bash
# .env.local
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature Flags
NEXT_PUBLIC_ENABLE_DEBUG=false
NEXT_PUBLIC_MAX_MESSAGE_LENGTH=2000

# Analytics (optional)
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX

# Sentry (optional)
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
```

### Runtime Config

```typescript
// lib/config.ts
export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    timeout: 30000,
  },
  chat: {
    maxMessageLength: parseInt(
      process.env.NEXT_PUBLIC_MAX_MESSAGE_LENGTH || "2000",
    ),
    streamingDelay: 10, // ms between tokens
  },
  ui: {
    enableDebug: process.env.NEXT_PUBLIC_ENABLE_DEBUG === "true",
    sidebarWidth: 280,
    mobileBreakpoint: 768,
  },
} as const;
```

---

## 14. Deployment Checklist

### Pre-deployment

- [ ] Run type checking: `tsc --noEmit`
- [ ] Run linting: `eslint . --fix`
- [ ] Run tests: `npm test`
- [ ] Build production: `npm run build`
- [ ] Check bundle size: Analyze with `@next/bundle-analyzer`
- [ ] Test on mobile devices
- [ ] Verify accessibility with Lighthouse
- [ ] Review error handling paths

### Vercel Deployment

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "env": {
    "NEXT_PUBLIC_API_URL": "@api-url"
  }
}
```

### Performance Targets

- **Lighthouse Score:** 90+ (all categories)
- **First Contentful Paint:** < 1.5s
- **Time to Interactive:** < 3.5s
- **Largest Contentful Paint:** < 2.5s
- **Bundle Size:** < 200KB (initial JS)

---

## 15. Future Enhancements

### Phase 2 Features

- [ ] Dark mode toggle (system preference detection)
- [ ] Thread search and filtering
- [ ] Export chat as PDF/Markdown
- [ ] Share thread via link
- [ ] Voice input for messages
- [ ] Video timestamp citations (jump to relevant section)
- [ ] Multi-language support (i18n)
- [ ] Custom user preferences (message density, font size)

### Advanced Features

- [ ] Real-time collaboration (multiple users in same thread)
- [ ] Suggested follow-up questions
- [ ] Video highlights extraction
- [ ] Integration with note-taking apps
- [ ] Browser extension for quick access
- [ ] Mobile app (React Native/Expo)

---

## 16. Development Workflow

### Quick Start

```bash
# Install dependencies
pnpm install

# Set up environment
cp .env.example .env.local

# Start dev server
pnpm dev

# Open browser at http://localhost:3000
```

### Development Scripts

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint . --ext .ts,.tsx",
    "lint:fix": "eslint . --ext .ts,.tsx --fix",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test",
    "format": "prettier --write \"**/*.{ts,tsx,json,md}\"",
    "analyze": "ANALYZE=true next build"
  }
}
```

### Git Workflow

```bash
# Feature branch
git checkout -b feature/chat-streaming

# Commit conventions
git commit -m "feat(chat): implement SSE streaming for messages"
git commit -m "fix(sidebar): resolve thread selection bug"
git commit -m "docs(readme): update installation steps"
git commit -m "style(chat): improve message bubble spacing"

# Types: feat, fix, docs, style, refactor, test, chore
```

---

## 17. Key Behavioral Guidelines

### System Prompt Context (for AI Assistant)

When the AI assistant interacts with users in the chat:

1. **Educational Focus:** Frame responses in an educational, explanatory manner
2. **Video Context Awareness:** Always reference the video context when answering
3. **Source Attribution:** When possible, cite specific parts of the transcript
4. **Clarification Prompts:** If a question is ambiguous, ask for clarification
5. **Respectful Tone:** Maintain a helpful, patient, and encouraging tone

### Example Welcome Message

```typescript
// First message when chat initializes
const welcomeMessage = {
  sender: "ai",
  content: `👋 Hi! I've processed the video "${videoTitle}". 

Here's a quick summary:
${summary}

Feel free to ask me anything about the content, concepts explained, or specific details from the video!`,
  created_at: new Date().toISOString(),
};
```

### Error Recovery Messaging

```typescript
// User-friendly error messages
const errorMessages = {
  invalidUrl:
    "Hmm, that doesn't look like a valid YouTube URL. Could you try again? Example: https://www.youtube.com/watch?v=xxxxx",

  noTranscript:
    "Unfortunately, this video doesn't have captions available. I need captions to chat about the content. Try another video?",

  processingFailed:
    "I had trouble processing that video. This could be temporary. Want to try again?",

  streamingError:
    "Oops! My response got interrupted. Let me try that again. Click the retry button.",
};
```

---

## 18. Resources & References

### Documentation

- [Next.js App Router Docs](https://nextjs.org/docs/app)
- [Vercel AI SDK Docs](https://sdk.vercel.ai/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)

### Design Inspiration

- [Linear App](https://linear.app/) - Clean, minimalist chat UI
- [ChatGPT UI](https://chat.openai.com/) - Message streaming patterns
- [Discord](https://discord.com/) - Thread/channel navigation

### Code Examples

- [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot) - Reference implementation
- [Next.js Commerce](https://github.com/vercel/commerce) - App Router patterns

---

## 19. Success Metrics

### User Experience Metrics

- **Time to First Message:** < 5 seconds after video processing
- **Message Send Latency:** < 500ms to show user message
- **Streaming Start Time:** < 1 second for first token
- **Thread Switch Time:** < 300ms

### Technical Metrics

- **API Response Time:** P95 < 2 seconds
- **Error Rate:** < 1% of requests
- **Uptime:** 99.9%
- **Bundle Size:** < 200KB initial load

---

## 20. Constraints & Limitations

### Critical Limitations

1. **NO Browser Storage APIs**
   - Cannot use `localStorage`, `sessionStorage`, or IndexedDB
   - All state must be managed in-memory or via React state
   - Thread persistence handled by backend only

2. **Streaming Only**
   - All AI responses must use SSE streaming
   - No polling or WebSocket alternatives

3. **Single User**
   - No authentication in PoC phase
   - No multi-user support initially

4. **Desktop-First**
   - Mobile experience is secondary priority
   - Optimize for desktop (1280px+) first
