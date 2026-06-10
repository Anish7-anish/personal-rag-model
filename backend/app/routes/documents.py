from fastapi import APIRouter, Query

from app.config import LOG_PATH, TRACE_LOG_PATH
from app.core.document_store import get_document_store
from app.core.rag_logger import read_recent_jsonl


router = APIRouter()


@router.get("/documents")
def list_documents(limit: int = Query(default=100, ge=1, le=500)):
    store = get_document_store()
    documents = store.list_documents(limit=limit)
    return {
        "documents": documents,
        "count": len(documents),
        "total_chunks": store.count_chunks(),
    }


@router.get("/documents/{document_id}/chunks")
def get_document_chunks(document_id: str, limit: int = Query(default=200, ge=1, le=500)):
    store = get_document_store()
    document = store.get_document(document_id)
    chunks = store.get_document_chunks(document_id, limit=limit)
    return {
        "document": document,
        "count": len(chunks),
        "chunks": chunks,
    }


@router.get("/debug/query-logs")
def recent_query_logs(limit: int = Query(default=20, ge=1, le=200)):
    return {"entries": read_recent_jsonl(LOG_PATH, limit=limit)}


@router.get("/debug/traces")
def recent_trace_logs(limit: int = Query(default=50, ge=1, le=500)):
    return {"entries": read_recent_jsonl(TRACE_LOG_PATH, limit=limit)}
