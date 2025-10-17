# backend/app/routes/query.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from app.core.vectorstore import get_vectorstore
from app.config import OLLAMA_MODEL

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


@router.post("/query")
async def query_docs(request: QueryRequest):
    """
    Retrieve top-k relevant chunks from Chroma and query Ollama model.
    """
    try:
        query = request.query
        top_k = request.top_k

        # Get stored embeddings
        db = get_vectorstore()
        docs = db.similarity_search(query, k=top_k)

        # Combine context text
        context = "\n\n".join([d.page_content for d in docs])

        # Prepare the prompt
        prompt = f"""You are a helpful assistant.
Answer the question using the following context only.
If you don't know, say you don't know.

Context:
{context}

Question:
{query}

Answer:
"""

        # Send to Ollama (local inference)
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt},
            stream=False,
            timeout=120,
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error contacting Ollama API")

        output = response.json().get("response", "").strip()
        return {"answer": output, "sources": [d.metadata for d in docs]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
