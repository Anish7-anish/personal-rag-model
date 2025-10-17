import os
from pathlib import Path
from fastapi import UploadFile
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader

BASE_UPLOAD_DIR = Path("backend/data/uploads")
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
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    return chunks
