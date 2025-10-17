# backend/app/core/vectorstore.py
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.config import CHROMA_DIR

# Initialize embeddings model (local — no OpenAI key needed)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vectorstore():
    """Create or load a persistent Chroma vector store."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    db = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )
    return db
