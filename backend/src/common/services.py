import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from src.core.config import settings

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.EMBEDDING_MODEL,
)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model=settings.SMART_LLM_MODEL,
)
