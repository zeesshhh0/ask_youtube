"use client";

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import type { Thread, ChatState, ChatContextValue } from "@/lib/types";
import { apiClient } from "@/lib/api/client";

// Initial state
const initialState: ChatState = {
  threads: [],
  activeThreadId: null,
  isSidebarOpen: false,
  isProcessing: false,
};

// Action types
type ChatAction =
  | { type: "SET_ACTIVE_THREAD"; threadId: string | null }
  | { type: "ADD_THREAD"; thread: Thread }
  | { type: "REMOVE_THREAD"; threadId: string }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "SET_SIDEBAR_OPEN"; isOpen: boolean }
  | { type: "SET_PROCESSING"; isProcessing: boolean }
  | { type: "SET_THREADS"; threads: Thread[] };

// Reducer
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "SET_ACTIVE_THREAD":
      return { ...state, activeThreadId: action.threadId };

    case "ADD_THREAD":
      // Avoid duplicates
      if (state.threads.some((t) => t.thread_id === action.thread.thread_id)) {
        return state;
      }
      return {
        ...state,
        threads: [action.thread, ...state.threads],
      };

    case "REMOVE_THREAD":
      return {
        ...state,
        threads: state.threads.filter((t) => t.thread_id !== action.threadId),
        activeThreadId:
          state.activeThreadId === action.threadId
            ? null
            : state.activeThreadId,
      };

    case "TOGGLE_SIDEBAR":
      return { ...state, isSidebarOpen: !state.isSidebarOpen };

    case "SET_SIDEBAR_OPEN":
      return { ...state, isSidebarOpen: action.isOpen };

    case "SET_PROCESSING":
      return { ...state, isProcessing: action.isProcessing };

    case "SET_THREADS":
      return { ...state, threads: action.threads };

    default:
      return state;
  }
}

// Context
const ChatContext = createContext<ChatContextValue | null>(null);

// Provider component
export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  useEffect(() => {
    async function loadThreads() {
      try {
        const threads = await apiClient.chat.getThreads();
        dispatch({ type: "SET_THREADS", threads });
      } catch (error) {
        console.error("Failed to load threads:", error);
      }
    }
    loadThreads();
  }, []);

  const setActiveThread = useCallback((threadId: string | null) => {
    dispatch({ type: "SET_ACTIVE_THREAD", threadId });
  }, []);

  const addThread = useCallback((thread: Thread) => {
    dispatch({ type: "ADD_THREAD", thread });
  }, []);

  const removeThread = useCallback((threadId: string) => {
    dispatch({ type: "REMOVE_THREAD", threadId });
  }, []);

  const toggleSidebar = useCallback(() => {
    dispatch({ type: "TOGGLE_SIDEBAR" });
  }, []);

  const setProcessing = useCallback((isProcessing: boolean) => {
    dispatch({ type: "SET_PROCESSING", isProcessing });
  }, []);

  const value: ChatContextValue = {
    ...state,
    setActiveThread,
    addThread,
    removeThread,
    toggleSidebar,
    setProcessing,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

// Hook for consuming context
export function useChatContext(): ChatContextValue {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
