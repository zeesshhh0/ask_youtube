## 1. Project Overview

**Name:** Ask Youtube  
**Type:** Chatbot for YouTube Videos  
**Goal:** Create a "Chat with Video" interface where users can ask questions about YouTube content.
**Priority:**

1. Chat with Video (RAG Pipeline) - **Primary Focus**

---

## 2. Tech Stack

### Core Framework

- **Language:** Python 3.10+
- **Backend Framework:** FastAPI
- **Package Manager:** uv (modern Python package manager)

### LangGraph & LangChain

- **Orchestration:** Direct Agent (`langchain.agents`)
  - `create_agent` - Direct agent creation
  - `AgentState` - State management for agent
  - `AsyncSqliteSaver` - Async checkpointing for state persistence
- **LLM Framework:** LangChain (`langchain-classic`, `langchain-google-genai`)
- **LLM Provider:** Google Gemini (via `langchain-google-genai`)
  - Fast LLM: `gemini-2.5-flash` (for speed)
  - Smart LLM: `gemini-2.5-pro` (for complex reasoning)
- **Observability:** LangSmith (for prompt management and tracing)

### Vector Database & Embeddings

- **Vector Database:** ChromaDB (`chromadb`)
- **Embedding Model:** Google Gemini Embeddings (`gemini-embedding-001`)

### Database & Persistence

- **Application Database:** SQLite (`aiosqlite` for async operations)
- **Checkpointing:** LangGraph `AsyncSqliteSaver` (SQLite)
- **Architecture:** Dual-database approach (see Database Architecture section)

### External APIs

- **Transcription:** YouTube Transcript API (`youtube-transcript-api`)

---

## 3. Database Architecture

**Rationale:** Separate concerns between LangGraph state management and application data.

#### Database 1: `checkpoints.db` (Agent State)

- **Purpose:** Store conversation checkpoints, thread states, and agent execution history
- **Managed by:** `AsyncSqliteSaver` (LangChain manages schema internally)
- **Tables:** Auto-managed by checkpointer
  - `checkpoints` - Stores state snapshots
  - `checkpoint_writes` - Stores pending writes
- **Usage:** Thread continuity, state recovery, conversation resumption

#### Database 2: `app.db` (Application Data)

- **Purpose:** Store business logic data (videos, threads metadata, user messages)
- **Managed by:** Application code (manual schema migrations)
- **Tables:** See Database Schema section below

#### Connection Pattern

```python
# Checkpoint database (Agent)
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncSqliteSaver.from_conn_string("checkpoints.db")
# checkpointer is passed to create_agent during initialization

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

## 6. Agent State Management

### State Definition (YTAgentState)

The agent uses a typed state definition to manage context:

```python
class YoutubeVideo(TypedDict):
    video_id: str
    title: str
    summary: str

class YTAgentState(AgentState):
    videos: List[YoutubeVideo]
```

### Middleware (`inject_video_summaries`)

A dynamic prompt middleware injects active video summaries into the system prompt:

```python
@dynamic_prompt
def inject_video_summaries(request: ModelRequest) -> str:
    # Fetches active videos from state
    # Formats them into the system prompt
    # Returns updated prompt
```

---

## 7. Agent Checkpointing

### Checkpointing Setup

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents import create_agent

# Initialize agent with checkpointer
async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    agent = create_agent(
        model=llm,
        tools=[retrieve_context],
        middleware=[inject_video_summaries],
        state_schema=YTAgentState,
        checkpointer=checkpointer,
        debug=True
    )
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

## 8. Workflow (Direct Agent)

### Agent Logic

**Trigger:** User sends a message via `POST /chat/{thread_id}/message`
**System Prompt:** Pulled from LangSmith (`ask_youtube_agent_system_prompt`)

#### Execution Flow

1.  **Input:** User message received.
2.  **Middleware:** `inject_video_summaries` updates the system prompt with context about active videos (title, summary).
3.  **LLM Processing:** The LLM decides whether to answer directly or use tools.
4.  **Tool Execution:** If needed, the agent calls `retrieve_context`.
5.  **Response:** The agent generates the final response.

#### Tools

1.  **`retrieve_context`**
    - **Purpose:** Search video transcripts for specific details.
    - **Input:** Query string.
    - **Process:**
      - Extracts video IDs from state (`videos`).
      - Performs similarity search in `vector_store` (ChromaDB) filtering by valid video IDs.
      - Groups results by video and chapter.
      - Formats the output with timestamps and transcripts.
    - **Output:** Serialized context string + retrieved documents (for metadata).

---

## 9. API Endpoints

### Thread Management

#### `POST /api/v1/threads`

Initialize chat, ingest YouTube video.

**Request:**

```json
{
  "video_url": "https://www.youtube.com/watch?v=..."
}
```

**Response:**

```json
{
  "thread_id": "uuid-here",
  "title": "Video Title",
  "summary": "Video summary..."
}
```

#### `GET /api/v1/threads`

List all user conversations (paginated).

**Response:**

```json
[
  {
    "thread_id": "6e0e092e-94f5-49cd-9202-8b43106f015a",
    "created_at": "2026-01-31T11:02:43.793765",
    "title": "dfsdfsfdsa"
  }
]
```

#### `DELETE /api/v1/threads/{id}`

Delete a conversation.

### Chat Interaction

#### `POST /api/v1/threads/{id}/messages`

Send a user question.

**Request:**

```json
{
  "thread_id": "id",
  "content": "User question here"
}
```

#### `GET /api/v1/threads/{id}/messages`

Get chat history.

**Response:**

```json
{
  "thread_id": "id",
  "messages": [
    {
      "message_id": 123,
      "role": "human",
      "content": "Hello",
      "metadata": {}
    }
  ]
}
```

---

## 10. Agent Best Practices

### Tool Design Principles

1.  **Clear Docstrings:** Essential for the LLM to understand when to use the tool.
2.  **Typed Arguments:** Use type hints for tool arguments.
3.  **Context Awareness:** Tools access `runtime.state` to get context (like active videos).

### Debugging

```python
# Enable debug mode on agent creation
agent = create_agent(..., debug=True)
```

### Prompt Management

- Use **LangSmith** to manage and version system prompts.
- Use middleware (`@dynamic_prompt`) for dynamic context injection.

---

## 11. Project Structure

```
backend/
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
