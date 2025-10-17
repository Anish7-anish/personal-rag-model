from fastapi import APIRouter, UploadFile, File
from app.core.utils import save_upload, load_and_split
from app.core.vectorstore import get_vectorstore

router = APIRouter()

@router.post("/upload")
async def upload_doc(file: UploadFile = File(...)):
    file_path = save_upload(file)
    docs = load_and_split(file_path)
    db = get_vectorstore()
    db.add_documents(docs)
    db.persist()
    return {
        "status": "success",
        "message": f"Indexed {len(docs)} chunks from {file.filename}",
    }