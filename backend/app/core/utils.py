import os
import re
from pathlib import Path
from fastapi import UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from app.config import UPLOAD_DIR


BASE_UPLOAD_DIR = Path(UPLOAD_DIR)
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload(file: UploadFile) -> str:
    """Save uploaded file to disk and return the saved path."""
    file_path = BASE_UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return str(file_path)

def load_and_split(file_path: str):
    """Load and chunk a file into text segments."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path)
    elif ext in [".doc", ".docx"]:
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    documents = loader.load()
    filename = Path(file_path).name
    header = f"Document: {filename}\n"

    if ext == ".pdf":
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    else:
        splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)

    chunks = splitter.split_documents(documents)
    for chunk in chunks:
        cleaned = re.sub(r"\s+", " ", chunk.page_content).strip()
        chunk.page_content = f"{header}{cleaned}".strip()
    return chunks
