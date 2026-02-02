// Chat Thread
export interface Thread {
  thread_id: string;
  video_id: string;
  title: string;
  summary: string;
  created_at: string;
}

// Chat Message
export interface Message {
  message_id: number;
  sender: "user" | "ai";
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

// API Request/Response types
export interface InitRequest {
  youtube_url: string;
}

export interface InitResponse {
  thread_id: string;
  video_id: string;
  title: string;
  summary: string;
}

export interface HistoryResponse {
  thread_id: string;
  video_id: string;
  messages: Message[];
}

// SSE Stream Events
export interface StreamTokenEvent {
  type: "token";
  content: string;
}

export interface StreamSourcesEvent {
  type: "sources";
  chunks: Array<{
    text: string;
    start_time?: number;
    end_time?: number;
  }>;
}

export interface StreamEndEvent {
  type: "end";
  message_id: number;
}

export interface StreamErrorEvent {
  type: "error";
  message: string;
}

export type StreamEvent =
  | StreamTokenEvent
  | StreamSourcesEvent
  | StreamEndEvent
  | StreamErrorEvent;

// Video metadata
export interface VideoMetadata {
  video_id: string;
  title: string;
  channel: string;
  duration: string;
  thumbnail_url: string;
  published_at: string;
}

// UI State
export interface ChatState {
  threads: Thread[];
  activeThreadId: string | null;
  isSidebarOpen: boolean;
  isProcessing: boolean;
}

export interface ChatActions {
  setActiveThread: (threadId: string | null) => void;
  addThread: (thread: Thread) => void;
  removeThread: (threadId: string) => void;
  toggleSidebar: () => void;
  setProcessing: (isProcessing: boolean) => void;
}

export type ChatContextValue = ChatState & ChatActions;
