# backend/app/core/vectorstore.py
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import CHROMA_DIR

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vectorstore():
    """Create or load a persistent Chroma vector store."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
