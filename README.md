# Ask YouTube

Ask YouTube is a full-stack web application that allows users to chat with YouTube videos. By providing a YouTube video URL, the application fetches the video's transcript and uses a Large Language Model (LLM) to answer your questions accurately based on the content of the video.

## Tech Stack

### Frontend

- **Framework**: [Next.js](https://nextjs.org/) (React 19)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **Components**: [shadcn/ui](https://ui.shadcn.com/) & Radix UI
- **Package Manager**: pnpm

### Backend

- **Language**: Python 3.13+
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI/LLM**: [LangChain](https://python.langchain.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), and Google GenAI
- **Database**: [SQLModel](https://sqlmodel.tiangolo.com/) (with PostgreSQL/SQLite support)
- **Tooling**: `uv` for dependency management & running

## Getting Started

### Prerequisites

- Node.js & `pnpm` installed
- Python 3.13+ & `uv` installed
- Appropriate API keys (e.g., Google Gemini API key) set in your backend environment variables.

### Running the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies and start the FastAPI server using `uv`:
   ```bash
   uv run -m src.main
   ```
   The backend will typically run on `http://localhost:8000`.

### Running the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Start the development server:
   ```bash
   pnpm dev
   ```
   The frontend will be available at `http://localhost:3000`.

## Architecture

1. **Transcript Extraction**: The backend uses `youtube-transcript-api` to pull down the transcript of the requested video.
2. **AI Processing**: LangChain and LangGraph manage the conversational state and LLM prompt generation to answer user queries with the video context.
3. **Chat Interface**: The Next.js frontend provides a clean, modern chat UI mimicking a standard conversational agent experience.
