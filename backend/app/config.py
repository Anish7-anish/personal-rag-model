import os
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = os.getcwd()

UPLOAD_DIR = os.path.join(BASE_DIR, "backend", "data", "uploads")
CHROMA_DIR = os.path.join(BASE_DIR, "backend", "chroma_store")

# Create folders if not exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# Ollama local model configuration
# You can change the model name in .env file
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
