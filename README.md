# Ask Youtube Frontend Development Prompt

You are an expert Senior Frontend Engineer specializing in Next.js, TypeScript, Tailwind CSS, shadcn/ui, and the Vercel AI SDK. Your task is to build a complete "Chat with Video" interface for educational YouTube content.

## Project Overview

**Name:** Ask Youtube  
**Goal:** Create a minimalist, clean chat interface where users can ask questions about YouTube videos using AI-powered RAG (Retrieval-Augmented Generation).  
**Tech Stack:** Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui, Vercel AI SDK

## Core Requirements

### 1. Technology Stack

**Framework & Language:**

- Next.js 14+ with App Router
- TypeScript for all code
- Node.js 18+
- pnpm as package manager

**UI & Styling:**

- Tailwind CSS 3.x for styling
- shadcn/ui components:
  - `Sheet` for sidebar drawer
  - `Button`, `Input`, `Textarea` for interactions
  - `ScrollArea` for message lists
  - `Card` for content containers
  - `Skeleton` for loading states
  - `Avatar` for message senders
  - `Separator`, `Badge` for UI elements

**AI Integration:**

- Vercel AI SDK (`ai` package)
- Primary hook: `useChat` for streaming responses
- Backend: REST API with Server-Sent Events (SSE)

**State Management:**

- React hooks (`useState`, `useReducer`) for local state
- React Context for global chat state
- Vercel AI SDK built-in state for streaming
- NO localStorage/sessionStorage (critical constraint)

### 2. Application Structure

Create this exact folder structure:

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

components/
├── chat/
│   ├── ChatContainer.tsx          # Main chat orchestrator
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
└── providers/
    └── ChatProvider.tsx           # Global chat state context

lib/
├── api/
│   ├── client.ts             # API client functions
│   └── streamHandler.ts      # SSE stream handler
├── config.ts                 # Runtime configuration
├── errors.ts                 # Error handling utilities
└── types.ts                  # TypeScript interfaces
```

### 3. User Flows (Critical)

**Flow A: New Chat Initialization**

1. User lands on `/chat` → Display `VideoUrlPrompt` centered with empty state
2. User enters YouTube URL and submits:
   - Show loading skeleton with progress messages:
     - "Fetching transcript..."
     - "Generating embeddings..."
     - "Preparing chat..."
   - Call `POST /api/chat/init` with `{ youtube_url: "..." }`
3. On success:
   - Redirect to `/chat/[threadId]`
   - Display `VideoCard` with metadata
   - Show AI welcome message with video summary
   - Add thread to sidebar
   - Enable chat input
4. On error:
   - Show toast notification with helpful error message
   - Allow retry

**Flow B: Chat Conversation**

1. User on `/chat/[threadId]`:
   - Load history: `GET /api/chat/{threadId}/history`
   - Display messages with proper sender attribution
   - Auto-scroll to latest message
2. User types message and submits:
   - Disable input (prevent double-submit)
   - Add user message to UI immediately (optimistic update)
   - Show typing indicator
   - Call `POST /api/chat/{threadId}/message` with SSE streaming
3. Stream AI response:
   - Append tokens to message bubble in real-time
   - Update scroll position
   - Show source citations (if available in stream)
4. On stream complete:
   - Enable input
   - Clear typing indicator
5. On error:
   - Show error message in chat
   - Re-enable input with retry option

**Flow C: Thread Management**

1. Sidebar shows recent threads (sorted by `created_at DESC`)
2. Click thread → Navigate to `/chat/[threadId]` and load history
3. Click "New Chat" → Navigate to `/chat` (empty state)
4. Delete thread (future) → Show confirmation, call `DELETE /api/chat/{threadId}`

### 4. Backend API Integration

**API Base URL:** `http://localhost:8000` (configurable via env)

**Endpoints to implement:**

```typescript
// POST /chat/init
interface InitRequest {
  youtube_url: string;
}
interface InitResponse {
  thread_id: string;
  video_id: string;
  title: string;
  summary: string;
}

// GET /chat/{threadId}/history
interface HistoryResponse {
  thread_id: string;
  video_id: string;
  messages: Message[];
}

interface Message {
  message_id: number;
  sender: "user" | "ai";
  content: string;
  metadata?: any;
  created_at: string;
}

// POST /chat/{threadId}/message (SSE Streaming)
interface MessageRequest {
  content: string;
}

// SSE Event Format:
// event: message
// data: {"type": "token", "content": "The"}
// data: {"type": "sources", "chunks": [...]}
// data: {"type": "end", "message_id": 123}
// data: {"type": "error", "message": "..."}

// DELETE /chat/{threadId}
```

**SSE Stream Handler Implementation:**

```typescript
// lib/api/streamHandler.ts
export function handleSSEStream(
  threadId: string,
  content: string,
  onToken: (token: string) => void,
  onComplete: (messageId: number) => void,
  onError: (error: Error) => void,
) {
  const eventSource = new EventSource(
    `/api/chat/${threadId}/message?content=${encodeURIComponent(content)}`,
  );

  eventSource.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case "token":
        onToken(data.content);
        break;
      case "sources":
        // Handle source citations
        break;
      case "end":
        onComplete(data.message_id);
        eventSource.close();
        break;
      case "error":
        onError(new Error(data.message));
        eventSource.close();
        break;
    }
  });

  eventSource.onerror = () => {
    onError(new Error("Stream connection failed"));
    eventSource.close();
  };

  return () => eventSource.close(); // Cleanup
}
```

### 5. Component Specifications

**ChatContainer.tsx** (Main orchestrator)

```typescript
interface ChatContainerProps {
  threadId?: string;
  initialMessages?: Message[];
}

// Features:
// - Auto-scroll to bottom on new messages
// - Handle streaming responses via Vercel AI SDK
// - Manage message history
// - Coordinate ChatInput and ChatMessages

// Layout:
// ┌─────────────────────────────────────────┐
// │ ChatHeader (video info)                 │
// ├─────────────────────────────────────────┤
// │                                         │
// │ ChatMessages (scrollable)               │
// │                                         │
// ├─────────────────────────────────────────┤
// │ ChatInput (fixed bottom)                │
// └─────────────────────────────────────────┘
```

**VideoUrlPrompt.tsx** (Initial state)

```typescript
interface VideoUrlPromptProps {
  onSubmit: (url: string) => Promise<void>;
  isLoading: boolean;
}

// UI States:
// 1. Empty: Input field + "Start Chat" button
// 2. Loading: Skeleton + progress messages
// 3. Error: Error message + retry button

// Validation: Must be valid YouTube URL
// Example: https://www.youtube.com/watch?v=xxxxx
```

**MessageBubble.tsx** (Individual messages)

```typescript
interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  showAvatar?: boolean;
}

// Styling:
// - User messages: Right-aligned, blue background (bg-blue-600)
// - AI messages: Left-aligned, muted background (bg-gray-100 dark:bg-gray-800)
// - Show streaming cursor (pulsing) when isStreaming=true
// - Markdown rendering for AI responses
// - Timestamp on hover
```

**Sidebar.tsx** (Thread navigation)

```typescript
interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  onThreadSelect: (threadId: string) => void;
  onNewChat: () => void;
}

// shadcn Sheet configuration:
// - Side: "left"
// - Width: 280px
// - Close on thread select (mobile)
// - Persistent on desktop (>= 768px)

// Layout:
// ┌─────────────────────┐
// │ [New Chat] Button   │
// ├─────────────────────┤
// │ ThreadList          │
// │ ├─ Thread 1         │
// │ ├─ Thread 2 (active)│
// │ └─ Thread 3         │
// └─────────────────────┘
```

**ChatInput.tsx** (Message composition)

```typescript
interface ChatInputProps {
  onSubmit: (message: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}

// Features:
// - Auto-resize textarea
// - Enter to submit, Shift+Enter for newline
// - Disabled state during streaming
// - Submit button with loading spinner
// - Max length: 2000 characters
```

### 6. State Management

**Global State (React Context)**

```typescript
// context/ChatContext.tsx
interface ChatContextState {
  threads: Thread[];
  activeThreadId: string | null;
  isSidebarOpen: boolean;
  isProcessing: boolean;

  // Actions
  setActiveThread: (threadId: string) => void;
  addThread: (thread: Thread) => void;
  removeThread: (threadId: string) => void;
  toggleSidebar: () => void;
}

// Provider wraps entire app in app/layout.tsx
```

**Vercel AI SDK Integration**

```typescript
// In ChatContainer.tsx
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
  api: `/api/chat/${threadId}/message`,
  streamMode: "text",
  onFinish: (message) => {
    // Save to history, update UI
  },
  onError: (error) => {
    // Show error toast
  },
});
```

### 7. Styling & Design

**Color Palette (Tailwind CSS)**

```css
/* Light Mode */
--background: 0 0% 100%;
--foreground: 222.2 84% 4.9%;
--primary: 221.2 83.2% 53.3%; /* Blue for user messages */
--muted: 210 40% 96.1%; /* AI message background */

/* Dark Mode */
--background: 222.2 84% 4.9%;
--foreground: 210 40% 98%;
--primary: 217.2 91.2% 59.8%;
--muted: 217.2 32.6% 17.5%;
```

**Typography**

- Font: Inter or system-ui
- Body text: 1rem (16px)
- Message bubbles: Comfortable padding (px-4 py-2)
- Rounded corners: rounded-2xl for bubbles

**Message Styling**

```typescript
// User Message
className =
  "ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-blue-600 text-white px-4 py-2";

// AI Message
className =
  "mr-auto max-w-[80%] rounded-2xl rounded-tl-sm bg-gray-100 dark:bg-gray-800 px-4 py-2";

// Streaming Cursor
className = "inline-block w-2 h-4 bg-current animate-pulse";
```

**Responsive Design**

- Mobile (< 768px): Sidebar as overlay (Sheet)
- Desktop (>= 768px): Persistent sidebar
- Chat input: Fixed at bottom, full width
- Messages: Stack vertically with gap-3

### 8. Critical Constraints & Requirements

**MUST DO:**

1. ✅ Use TypeScript for all files
2. ✅ Use shadcn/ui components (Sheet, Button, Input, ScrollArea, Card, Skeleton)
3. ✅ Implement SSE streaming for AI responses
4. ✅ Auto-scroll to bottom on new messages
5. ✅ Show loading states during video processing
6. ✅ Handle errors gracefully with user-friendly messages
7. ✅ Implement optimistic updates (show user message immediately)
8. ✅ Support dark mode
9. ✅ Mobile responsive design
10. ✅ Accessible (ARIA labels, keyboard navigation)

**MUST NOT DO:**

1. ❌ Use localStorage or sessionStorage (critical - violates artifact constraints)
2. ❌ Use IndexedDB or any browser storage
3. ❌ Hardcode API URLs (use environment variables)
4. ❌ Ignore error handling
5. ❌ Create non-responsive layouts
6. ❌ Use inline styles (use Tailwind classes)
7. ❌ Skip TypeScript types
8. ❌ Forget to handle loading/error states

### 9. Implementation Checklist

**Phase 1: Project Setup**

- [ ] Create folder structure
- [ ] Set up environment variables

**Phase 2: Core Components**

- [ ] Create ChatProvider (global state)
- [ ] Build VideoUrlPrompt with validation
- [ ] Build MessageBubble (user + AI variants)
- [ ] Build ChatMessages with auto-scroll
- [ ] Build ChatInput with auto-resize
- [ ] Build ChatContainer (orchestrator)
- [ ] Build Sidebar with Sheet
- [ ] Build ThreadList and ThreadItem

**Phase 3: API Integration**

- [ ] Create API client (lib/api/client.ts)
- [ ] Implement SSE stream handler
- [ ] Create Next.js API route proxy
- [ ] Integrate Vercel AI SDK useChat hook
- [ ] Test streaming responses
- [ ] Implement error handling

**Phase 4: User Flows**

- [ ] Implement new chat initialization flow
- [ ] Implement chat conversation flow
- [ ] Implement thread switching
- [ ] Add loading states everywhere
- [ ] Add error boundaries

**Phase 5: Polish**

- [ ] Implement dark mode
- [ ] Add animations (smooth scroll, fade-in)
- [ ] Optimize performance (React.memo, useMemo)
- [ ] Add accessibility features
- [ ] Test on mobile devices
- [ ] Write README with setup instructions

### 10. Example Code Snippets

**API Client (lib/api/client.ts)**

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  chat: {
    init: async (youtubeUrl: string) => {
      const res = await fetch(`${API_BASE_URL}/chat/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: youtubeUrl }),
      });
      if (!res.ok) throw new Error("Failed to initialize chat");
      return res.json();
    },

    getHistory: async (threadId: string) => {
      const res = await fetch(`${API_BASE_URL}/chat/${threadId}/history`);
      if (!res.ok) throw new Error("Failed to fetch history");
      return res.json();
    },

    deleteThread: async (threadId: string) => {
      const res = await fetch(`${API_BASE_URL}/chat/${threadId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete thread");
      return res.json();
    },
  },
};
```

**Welcome Message Example**

```typescript
const welcomeMessage = {
  sender: "ai",
  content: `👋 Hi! I've processed the video "${videoTitle}". 

Here's a quick summary:
${summary}

Feel free to ask me anything about the content, concepts explained, or specific details from the video!`,
  created_at: new Date().toISOString(),
};
```

**Error Messages**

```typescript
const errorMessages = {
  invalidUrl:
    "Hmm, that doesn't look like a valid YouTube URL. Could you try again? Example: https://www.youtube.com/watch?v=xxxxx",

  noTranscript:
    "Unfortunately, this video doesn't have captions available. I need captions to chat about the content. Try another video?",

  processingFailed:
    "I had trouble processing that video. This could be temporary. Want to try again?",

  streamingError: "Oops! My response got interrupted. Let me try that again.",
};
```

### 11. Environment Configuration

Create `.env.local`:

```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature Flags
NEXT_PUBLIC_ENABLE_DEBUG=false
NEXT_PUBLIC_MAX_MESSAGE_LENGTH=2000
```

### 12. Success Criteria

Your implementation is successful when:

1. ✅ User can paste a YouTube URL and start a chat
2. ✅ Video processing shows clear progress feedback
3. ✅ AI responses stream in real-time (token by token)
4. ✅ Messages auto-scroll to bottom
5. ✅ Sidebar shows all chat threads
6. ✅ Thread switching works instantly
7. ✅ Mobile layout is fully functional
8. ✅ Dark mode works correctly
9. ✅ All error states show helpful messages
10. ✅ No console errors or warnings
11. ✅ TypeScript compiles without errors
12. ✅ UI is clean, minimal, and professional

### 13. Final Notes

**Design Philosophy:**

- Minimalist and clean (inspired by Linear, ChatGPT)
- Focus on conversation, not clutter
- Smooth animations and transitions
- Clear visual hierarchy
- Accessible to all users

**Performance Targets:**

- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Bundle Size: < 200KB initial JS

**AI Behavior:**

- Educational and explanatory tone
- Reference video context in responses
- Cite sources when possible
- Ask clarifying questions when needed
- Helpful, patient, encouraging

---

## Your Task

Build the complete Ask Youtube frontend following this specification exactly. Focus on:

1. **Clean, production-ready code** with TypeScript
2. **Pixel-perfect UI** using Tailwind CSS and shadcn/ui
3. **Smooth streaming experience** with Vercel AI SDK
4. **Robust error handling** at every step
5. **Mobile-responsive design** that works on all devices

Start with the project setup, then build components incrementally, testing each flow as you go. Ask clarifying questions if any requirement is unclear.

Good luck! 🚀
