## 1. Project Overview

**Name:** Explainium  
**Type:** Educational Chatbot for YouTube Videos  
**Goal:** Create a "Chat with Video" interface where users can ask questions about educational YouTube content. The system processes video transcripts using RAG (Retrieval-Augmented Generation) and generates educational questions.  
**Status:** Proof of Concept (PoC)  
**Priority:**

1. Chat with Video (RAG Pipeline) - **Primary Focus**

---

## 2. Tech Stack

### Core Framework

- **Language:** Python 3.10+
- **Backend Framework:** FastAPI
- **Package Manager:** uv (modern Python package manager)

### LangGraph & LangChain

- **Orchestration:** LangGraph 1.0+ (`langgraph`)
  - `StateGraph` - Graph-based workflow orchestration
  - `MessagesState` - Built-in state for chat workflows
  - `AsyncSqliteSaver` - Async checkpointing for state persistence
- **LLM Framework:** LangChain (`langchain-classic`, `langchain-google-genai`)
- **LLM Provider:** Google Gemini (via `langchain-google-genai`)
  - Fast LLM: `gemini-2.5-flash` (for speed)
  - Smart LLM: `gemini-2.5-pro` (for complex reasoning)

### Vector Database & Embeddings

- **Vector Database:** ChromaDB (`chromadb`)
- **Embedding Model:** Google Gemini Embeddings (`gemini-embedding-001`)

### Database & Persistence

- **Application Database:** SQLite (`aiosqlite` for async operations)
- **Checkpointing:** LangGraph `AsyncSqliteSaver`
- **Architecture:** Dual-database approach (see Database Architecture section)

### External APIs

- **Transcription:** YouTube Transcript API (`youtube-transcript-api`)

---

## 3. Database Architecture

**Rationale:** Separate concerns between LangGraph state management and application data.

#### Database 1: `checkpoints.db` (LangGraph State)

- **Purpose:** Store conversation checkpoints, thread states, and graph execution history
- **Managed by:** `AsyncSqliteSaver` (LangGraph manages schema internally)
- **Tables:** Auto-managed by LangGraph
  - `checkpoints` - Stores state snapshots
  - `checkpoint_writes` - Stores pending writes
- **Usage:** Thread continuity, state recovery, conversation resumption

#### Database 2: `app.db` (Application Data)

- **Purpose:** Store business logic data (videos, threads metadata, user messages)
- **Managed by:** Application code (manual schema migrations)
- **Tables:** See Database Schema section below

#### Connection Pattern

```python
# Checkpoint database (LangGraph)
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncSqliteSaver.from_conn_string("checkpoints.db")
graph = workflow.compile(checkpointer=checkpointer)

# Application database (FastAPI/SQLAlchemy)
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine("sqlite+aiosqlite:///app.db")
```

---

## 4. Database Schema (app.db)

### `yt_video` Table

```sql
CREATE TABLE yt_video (
    video_id TEXT PRIMARY KEY,           -- YouTube Video ID
    url TEXT NOT NULL,                   -- Original YouTube URL
    title TEXT,                          -- Video title (from oEmbed)
    author_name TEXT,                    -- Channel name
    thumbnail_url TEXT,                  -- Thumbnail URL
    transcript TEXT NOT NULL,            -- Full transcript text
    summary TEXT,                        -- AI-generated summary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `threads` Table

```sql
CREATE TABLE threads (
    thread_id TEXT PRIMARY KEY,          -- UUID for thread
    video_id TEXT NOT NULL,              -- FK to yt_video.video_id
    title TEXT,                          -- Thread title (usually video title)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES yt_video(video_id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX idx_threads_video_id ON threads(video_id);
```

### `messages` Table

```sql
CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,             -- FK to threads.thread_id
    sender TEXT NOT NULL,                -- 'user' or 'ai'
    content TEXT NOT NULL,               -- Message body
    metadata JSON,                       -- Optional: sources, tokens, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);

-- Index for faster history retrieval
CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

---

## 5. Vector Database Schema (ChromaDB)

### Collection Configuration

```python
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
client = chromadb.PersistentClient(
    path="./.chroma",
    settings=Settings(anonymized_telemetry=False)
)

# Collection per video (recommended for isolation)
collection = client.get_or_create_collection(
    name=f"video_{video_id}",
    metadata={
        "hnsw:space": "cosine",           # Similarity function
        "hnsw:construction_ef": 100,      # Build-time accuracy
        "hnsw:search_ef": 100             # Search-time accuracy
    }
)
```

### Document Schema

Each chunk stored with:

- `id`: `{video_id}_chunk_{index}` (e.g., `dQw4w9WgXcQ_chunk_0`)
- `documents`: Text chunk (1000 chars)
- `embeddings`: Gemini embedding vector (768 dimensions)
- `metadatas`:
  ```python
  {
      "video_id": "dQw4w9WgXcQ",
      "chunk_index": 0,
      "start_char": 0,
      "end_char": 1000,
      "timestamp_start": 0.0,    # Optional: if timestamps available
      "timestamp_end": 45.2      # Optional
  }
  ```

### Retrieval Parameters

```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,                # Retrieve top 5 chunks
    include=["documents", "metadatas", "distances"]
)
```

---

## 6. LangGraph State Management

### State Definition Patterns

#### Pattern 1: Built-in `MessagesState` (Chat Workflow)

Use for chat-based workflows with message history:

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage

def chat_node(state: MessagesState):
    messages = state['messages']
    # Process messages...
    response = llm.invoke(messages)
    return {'messages': [response]}

workflow = StateGraph(MessagesState)
workflow.add_node('chat', chat_node)
workflow.add_edge(START, 'chat')
workflow.add_edge('chat', END)

graph = workflow.compile(checkpointer=checkpointer)
```

### State Reducers (Advanced)

For complex state updates, use annotated reducers:

```python
from typing import Annotated
from operator import add

class RAGState(TypedDict):
    messages: Annotated[list, add]      # Append to list
    context: str                         # Replace value
    sources: Annotated[list, add]       # Append to list

# When node returns:
# {'messages': [new_msg]} -> appends to state['messages']
# {'context': new_context} -> replaces state['context']
```

---

## 7. LangGraph Checkpointing & Threads

### Checkpointing Setup

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

async def create_graph():
    # Create checkpointer (async context manager)
    async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
        workflow = StateGraph(MessagesState)
        # Add nodes and edges...
        graph = workflow.compile(checkpointer=checkpointer)
        return graph
```

### Thread Management

```python
from langchain_core.runnables import RunnableConfig

# Invoke with thread_id for state persistence
config = RunnableConfig(configurable={"thread_id": "thread_123"})

# First message in thread
response1 = await graph.ainvoke(
    {'messages': [HumanMessage("What is this video about?")]},
    config=config
)

# Continue conversation (state automatically restored)
response2 = await graph.ainvoke(
    {'messages': [HumanMessage("Can you elaborate?")]},
    config=config
)
```

### Checkpoint Features

- **State Resumption:** Continue conversations across API calls
- **State History:** Access previous checkpoints (time-travel debugging)
- **State Updates:** Manually update state at checkpoints
- **Branching:** Create alternate conversation paths from checkpoints

---

## 8. Workflows (LangGraph)

### Workflow A: Chat with Video (RAG Pipeline) - **Priority 1**

**Trigger:** User sends a message via `POST /chat/{thread_id}/message`  
**State Type:** `MessagesState`  
**Streaming:** Yes (using `.astream()`)

#### Graph Structure

```
START → retrieve_context → generate_response → END
                ↓ (conditional)
         context_summarizer (if context too large)
```

#### Nodes

1. **`retrieve_context`** (RAG Retrieval)
   - **Input:** `state['messages']` (latest user message)
   - **Process:**
     - Extract user query from last message
     - Generate embedding using Gemini
     - Query ChromaDB for top 5 relevant chunks
     - Retrieve chat history from `messages` table (last 10 messages)
   - **Output:** Update state with `context` key (retrieved chunks)

2. **`generate_response`** (LLM Generation)
   - **Input:** `state['messages']` + `state['context']`
   - **Process:**
     - Construct prompt: `[System] + [Context] + [History] + [Query]`
     - Stream response from Gemini LLM
     - Persist user message and AI response to `messages` table
   - **Output:** Append AIMessage to `state['messages']`

3. **`context_summarizer`** (Conditional - Future Enhancement)
   - **Trigger:** If conversation exceeds token limit
   - **Process:** Summarize older messages to compress context
   - **Output:** Replace older messages with summary

#### Conditional Edge Logic

```python
def should_summarize(state: MessagesState) -> str:
    # Calculate approximate token count
    total_tokens = estimate_tokens(state['messages'])
    if total_tokens > 8000:
        return "summarize"
    return "generate"

workflow.add_conditional_edges(
    "retrieve_context",
    should_summarize,
    {
        "summarize": "context_summarizer",
        "generate": "generate_response"
    }
)
```

---

## 9. API Endpoints

### Video Initialization

#### `POST /chat/init`

Initialize a new chat thread for a YouTube video.

**Request:**

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Process:**

1. Extract video ID from URL
2. Check if video exists in `yt_video` table
3. If not exists:
   - Fetch transcript using `YouTubeTranscriptApi`
   - Fetch metadata using YouTube oEmbed API
   - Generate summary using Gemini
   - Chunk transcript using `RecursiveCharacterTextSplitter`
   - Generate embeddings and store in ChromaDB
   - Save to `yt_video` table
4. Create new thread in `threads` table

**Response:**

```json
{
  "thread_id": "uuid-here",
  "video_id": "dQw4w9WgXcQ",
  "title": "Never Gonna Give You Up",
  "summary": "AI-generated summary..."
}
```

---

### Chat Interaction

#### `POST /chat/{thread_id}/message` (Streaming)

Send a message and receive streaming response.

**Request:**

```json
{
  "content": "What are the main arguments presented?"
}
```

**Process:**

1. Retrieve thread from `threads` table
2. Validate thread exists and get `video_id`
3. Save user message to `messages` table
4. Run LangGraph RAG workflow with streaming
5. Stream response chunks as Server-Sent Events (SSE)
6. Save final AI response to `messages` table

**Response (SSE Stream):**

```
event: message
data: {"type": "token", "content": "The"}

event: message
data: {"type": "token", "content": " main"}

event: message
data: {"type": "token", "content": " arguments"}

event: message
data: {"type": "sources", "chunks": [{"chunk_id": "...", "score": 0.85}]}

event: message
data: {"type": "end", "message_id": 123}
```

**Streaming Implementation:**

```python
from fastapi.responses import StreamingResponse

@router.post("/{thread_id}/message")
async def send_message(thread_id: str, message: MessageRequest):
    async def event_generator():
        config = {"configurable": {"thread_id": thread_id}}

        async for event in graph.astream(
            {'messages': [HumanMessage(message.content)]},
            config=config,
            stream_mode="values"  # or "updates" for delta streaming
        ):
            if 'messages' in event:
                chunk = event['messages'][-1].content
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

### Thread Management

#### `GET /chat/{thread_id}/history`

Retrieve message history for UI rendering.

**Response:**

```json
{
  "thread_id": "uuid-here",
  "video_id": "dQw4w9WgXcQ",
  "messages": [
    {
      "message_id": 1,
      "sender": "user",
      "content": "What is this video about?",
      "created_at": "2024-01-27T10:00:00Z"
    },
    {
      "message_id": 2,
      "sender": "ai",
      "content": "This video discusses...",
      "created_at": "2024-01-27T10:00:05Z"
    }
  ]
}
```

#### `DELETE /chat/{thread_id}`

Delete a thread and its messages.

**Process:**

1. Delete from `messages` table (CASCADE)
2. Delete from `threads` table
3. Optionally: Prune checkpoints from `checkpoints.db`

---

## 10. LangGraph Best Practices

### Node Design Principles

1. **Pure Functions:** Nodes should be deterministic given the same state
2. **Single Responsibility:** Each node handles one task
3. **State Updates:** Return dict with only fields to update
4. **Error Handling:** Use try/except and return error state

```python
def safe_node(state: MyState) -> dict:
    try:
        result = process(state['input'])
        return {'output': result, 'error': None}
    except Exception as e:
        return {'error': str(e)}
```

### Debugging

```python
# Enable debug mode for detailed logs
graph = workflow.compile(checkpointer=checkpointer, debug=True)

# Inspect state at checkpoints
checkpoints = await checkpointer.alist(config)
for checkpoint in checkpoints:
    print(checkpoint.state)
```

### Testing Workflows

```python
import pytest
from langgraph.graph import StateGraph

def test_chat_workflow():
    # Create graph without checkpointer for testing
    workflow = StateGraph(MessagesState)
    # ... add nodes ...
    graph = workflow.compile()

    # Test invocation
    result = graph.invoke({'messages': [HumanMessage("test")]})
    assert len(result['messages']) == 2  # User + AI message
```

### State Validation

```python
from pydantic import BaseModel, validator

class ValidatedState(BaseModel):
    transcript_text: str
    summary_text: str = ""

    @validator('transcript_text')
    def validate_transcript(cls, v):
        if len(v) < 100:
            raise ValueError("Transcript too short")
        return v

# Use in nodes
def node(state: dict) -> dict:
    validated = ValidatedState(**state)
    # Process validated state...
```

---

## 11. Project Structure

```
explainium_backend/
├── src/
│   ├── agents/
│   ├── api/
│   │   ├── main.py                   # FastAPI app
│   │   └── chat.py                   # Chat endpoints
│   ├── services/
│   │   └── youtube_tools.py          # YouTube API utilities
│   └── core/
│       ├── config.py                 # App configuration
│       └── logging.py                # Logging setup
├── checkpoints.db                    # LangGraph state (gitignored)
├── app.db                            # Application data (gitignored)
├── .chroma/                          # ChromaDB persistence (gitignored)
├── pyproject.toml
├── uv.lock
└── gemini.md                         # This file
```

---

## 12. Environment Variables

```bash
# .env
# Google AI
GOOGLE_API_KEY=your_gemini_api_key_here

# Database paths
CHECKPOINT_DB_PATH=checkpoints.db
APP_DB_PATH=app.db
CHROMA_DB_PATH=./.chroma

# LLM Configuration
FAST_LLM_MODEL=gemini-1.5-flash
SMART_LLM_MODEL=gemini-1.5-pro
EMBEDDING_MODEL=gemini-embedding-001

# Text Splitting
CHUNK_SIZE=1000
CHUNK_OVERLAP=100

# Retrieval
RETRIEVAL_K=5

# API
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 13. Next Steps & Improvements

### Immediate (POC Phase)

- [x] Implement RAG chat workflow with streaming
- [x] Set up dual-database architecture
- [x] Integrate ChromaDB with Gemini embeddings
- [x] Implement `POST /chat/init` endpoint
- [x] Implement `POST /chat/{thread_id}/message` with SSE streaming

### Short-term

- [ ] Add conditional edge for context summarization
- [ ] Implement proper error handling in nodes
- [ ] Add unit tests for workflows
- [ ] Add message metadata (sources, confidence scores)
- [ ] Implement thread deletion with checkpoint pruning

### Long-term

- [ ] Add WebSocket support for real-time streaming
- [ ] Implement conversation summarization
- [ ] Add user authentication & authorization
- [ ] Multi-modal support (video frames, screenshots)
- [ ] Deploy to production (consider LangGraph Cloud)
- [ ] Add conversation analytics and insights

---

## 14. Resources

### LangGraph Documentation

- [LangGraph Docs](https://docs.langchain.com/llms.txt)
- [State Management Guide](https://docs.langchain.com/oss/python/langgraph/graph-api#state)
- [Checkpointing](https://docs.langchain.com/oss/python/langgraph/persistence/)
- [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)

### Related Guides

- [Gemini API Docs](https://ai.google.dev/docs)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [FastAPI Streaming](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
