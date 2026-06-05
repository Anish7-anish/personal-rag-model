import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = str(BASE_DIR / "backend" / "data" / "uploads")
CHROMA_DIR = str(BASE_DIR / "backend" / "chroma_store")
FAISS_DIR = str(BASE_DIR / "backend" / "faiss_store")
STORE_DB_PATH = str(BASE_DIR / "backend" / "data" / "rag_store.sqlite3")

# Create folders if not exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(FAISS_DIR, exist_ok=True)

# RAG logs
LOG_DIR = str(BASE_DIR / "backend" / "data" / "logs")
LOG_PATH = str(Path(LOG_DIR) / "rag_queries.jsonl")
TRACE_LOG_PATH = str(Path(LOG_DIR) / "rag_trace.jsonl")
APP_LOG_PATH = str(Path(LOG_DIR) / "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

# Ollama local model configuration
# You can change the model name in .env file
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
TRACE_PREVIEW_CHARS = int(os.getenv("TRACE_PREVIEW_CHARS", "280"))
TRACE_MAX_CHUNKS_LOGGED = int(os.getenv("TRACE_MAX_CHUNKS_LOGGED", "200"))

# MongoDB logging (optional)
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "personal_rag")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "rag_logs")
