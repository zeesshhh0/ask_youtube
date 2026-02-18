import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.config import settings
from langchain_classic.storage import InMemoryStore
from langchain_classic.retrievers import ParentDocumentRetriever

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.EMBEDDING_MODEL,
)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model=settings.FASTEST_LLM_MODEL,
)

vector_store = Chroma(
    client=chroma_client,
    collection_name=settings.CHROMA_COLLECTION_NAME,
    embedding_function=embeddings
)