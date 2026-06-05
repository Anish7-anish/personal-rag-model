from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.core.document_store import get_document_store
from app.core.rag_logger import get_app_logger, log_trace_event, preview_text
from app.core.utils import compute_file_hash, load_and_split, save_upload


router = APIRouter()
logger = get_app_logger("personal_rag.upload")


@router.post("/upload")
async def upload_doc(file: UploadFile = File(...)):
    file_path = save_upload(file)
    chunks = load_and_split(file_path)
    content_hash = compute_file_hash(file_path)
    file_size = Path(file_path).stat().st_size

    store = get_document_store()
    result = store.upsert_document(
        file_path=file_path,
        content_hash=content_hash,
        file_size=file_size,
        chunks=chunks,
    )

    document = result["document"]
    log_trace_event(
        "upload.indexed",
        {
            "filename": document["filename"],
            "document_id": document["id"],
            "status": result["status"],
            "chunk_count": document["chunk_count"],
            "file_size": document["file_size"],
            "content_hash": document["content_hash"],
            "chunk_previews": [preview_text(chunk.page_content, 220) for chunk in chunks[:10]],
        },
        trace_id=document["id"],
    )
    logger.info(
        "Indexed filename=%s document_id=%s chunks=%s status=%s",
        document["filename"],
        document["id"],
        document["chunk_count"],
        result["status"],
    )
    for index, chunk in enumerate(chunks, start=1):
        logger.info(
            "Chunk %s/%s filename=%s chars=%s preview=%s",
            index,
            len(chunks),
            document["filename"],
            len(chunk.page_content),
            preview_text(chunk.page_content, 220),
        )

    return {
        "status": result["status"],
        "message": f"{result['status'].capitalize()} {document['chunk_count']} chunks for {document['filename']}",
        "document": document,
    }
