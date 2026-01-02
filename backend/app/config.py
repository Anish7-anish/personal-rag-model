import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = str(BASE_DIR / "backend" / "data" / "uploads")
CHROMA_DIR = str(BASE_DIR / "backend" / "chroma_store")
FAISS_DIR = str(BASE_DIR / "backend" / "faiss_store")

# Create folders if not exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(FAISS_DIR, exist_ok=True)

# RAG logs
LOG_DIR = str(BASE_DIR / "backend" / "data" / "logs")
LOG_PATH = str(Path(LOG_DIR) / "rag_queries.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)

# Ollama local model configuration
# You can change the model name in .env file
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
