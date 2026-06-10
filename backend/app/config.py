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

# Local Ollama defaults
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

# Hosted Groq defaults for free-tier usage
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

_requested_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
if _requested_provider:
    LLM_PROVIDER = _requested_provider
elif GROQ_API_KEY:
    LLM_PROVIDER = "groq"
else:
    LLM_PROVIDER = "ollama"

LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
if not LLM_MODEL:
    LLM_MODEL = GROQ_MODEL if LLM_PROVIDER == "groq" else OLLAMA_MODEL

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
if not LLM_BASE_URL:
    LLM_BASE_URL = GROQ_BASE_URL if LLM_PROVIDER == "groq" else OLLAMA_BASE_URL

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
if not LLM_API_KEY and LLM_PROVIDER == "groq":
    LLM_API_KEY = GROQ_API_KEY

LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", str(OLLAMA_TIMEOUT_SECONDS)))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
TRACE_PREVIEW_CHARS = int(os.getenv("TRACE_PREVIEW_CHARS", "280"))
TRACE_MAX_CHUNKS_LOGGED = int(os.getenv("TRACE_MAX_CHUNKS_LOGGED", "200"))

# MongoDB logging (optional)
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "personal_rag")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "rag_logs")
