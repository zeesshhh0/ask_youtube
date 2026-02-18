// ─── Thread ──────────────────────────────────────────────────────────────────

/** A chat thread as returned by GET /api/v1/threads */
export interface ThreadListItem {
  thread_id: string;
  title: string | null;
  video_id: string;
  created_at: string; // ISO 8601
}

/** Full thread info (used in UI state after creation) */
export interface Thread {
  thread_id: string;
  video_id: string;
  title: string | null;
  summary: string | null;
  created_at: string;
}

// ─── Messages ─────────────────────────────────────────────────────────────────

/** A single message as returned by GET /api/v1/threads/{id}/messages */
export interface MessageResponse {
  message_id: number;   // 0-based index in LangGraph state
  role: "human" | "ai";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;   // ISO 8601
}

/** Local UI message shape (maps role → sender for display) */
export interface Message {
  message_id: number;
  sender: "user" | "ai";
  content: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

// ─── API Request / Response ───────────────────────────────────────────────────

/** POST /api/v1/threads request body */
export interface CreateThreadRequest {
  video_url: string;
}

/** POST /api/v1/threads response */
export interface CreateThreadResponse {
  thread_id: string;
  video_id: string;
  title: string | null;
  summary: string | null;
}

/** GET /api/v1/threads/{id}/messages response */
export interface ThreadMessagesResponse {
  thread_id: string;
  messages: MessageResponse[];
}

/** DELETE /api/v1/threads/{id} response */
export interface DeleteThreadResponse {
  success: boolean;
  thread_id: string;
}

// ─── SSE Stream Events ────────────────────────────────────────────────────────

/** Partial AI response chunk */
export interface StreamTokenEvent {
  type: "token";
  content: string;
}

/** End of stream */
export interface StreamEndEvent {
  type: "end";
}

export type StreamEvent = StreamTokenEvent | StreamEndEvent;

// ─── UI State ─────────────────────────────────────────────────────────────────

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
