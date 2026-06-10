import re
import uuid
from pathlib import Path
from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import LLM_MODEL, LLM_PROVIDER
from app.core.document_store import get_document_store
from app.core.llm_provider import generate_text
from app.core.rag_logger import (
    get_app_logger,
    log_query_event,
    log_trace_event,
    preview_text,
)


router = APIRouter()
logger = get_app_logger("personal_rag.query")

TOP_K = 8
MAX_CONTEXT_CHUNKS = 4
WORK_INTENT_TERMS = {
    "role",
    "work",
    "worked",
    "working",
    "job",
    "position",
    "employment",
    "experience",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "now",
    "of",
    "on",
    "or",
    "right",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "who",
    "with",
    "you",
    "your",
}


class QueryRequest(BaseModel):
    query: str


def _extract_entity(query: str):
    match = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", query)
    if match:
        return match[0], True
    if "anish" in query.lower():
        return "Anish", False
    return None, False


def _infer_subject_from_sources(chunks):
    filenames = {Path(chunk["filename"]).stem for chunk in chunks if chunk.get("filename")}
    if len(filenames) != 1:
        return None
    name = next(iter(filenames))
    cleaned = re.sub(r"[_-]+", " ", name).strip()
    cleaned = re.sub(r"\bresume\b", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or None


def _infer_subject_from_context(context: str):
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    name_re = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$")
    for line in lines[:10]:
        if name_re.match(line) and not any(char.isdigit() for char in line):
            return line
    return None


def _extract_phrases(query: str):
    phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", query)
    return list(dict.fromkeys(phrases))


def _expand_phrase_queries(phrases, tokens):
    expanded = list(phrases)
    if tokens & WORK_INTENT_TERMS:
        for phrase in phrases:
            expanded.append(f"{phrase} Software Engineer")
            expanded.append(f"{phrase} role")
    return list(dict.fromkeys(expanded))


def _extract_role_for_org(context: str, org: str):
    if not org:
        return None
    escaped = re.escape(org)
    pattern = re.compile(rf"([A-Z][A-Za-z &/]+),\s*{escaped}", re.IGNORECASE)
    match = pattern.search(context)
    if match:
        return match.group(1).strip()
    return None


def _meaningful_tokens(query: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    return {
        token
        for token in tokens
        if token not in STOPWORDS and (len(token) > 2 or token in WORK_INTENT_TERMS)
    }


def _score_chunk(chunk: dict, query: str, tokens: set[str], phrase_queries: list[str]) -> int:
    text = chunk["content"].lower()
    filename = (chunk.get("filename") or "").lower()
    normalized_query = query.lower()
    score = 0

    if normalized_query and normalized_query in text:
        score += 30

    for phrase in phrase_queries:
        phrase_lower = phrase.lower()
        if phrase_lower in text:
            score += 20
        if phrase_lower in filename:
            score += 5

    for token in tokens:
        if len(token) <= 1:
            continue
        score += min(text.count(token), 6) * 3
        if token in filename:
            score += 2

    return score


def _retrieve_chunks(query: str, top_k: int = TOP_K):
    tokens = _meaningful_tokens(query)
    phrase_queries = _expand_phrase_queries(_extract_phrases(query), tokens)
    store = get_document_store()
    chunks = store.list_chunks()
    scored = []
    for chunk in chunks:
        score = _score_chunk(chunk, query, tokens, phrase_queries)
        if score > 0:
            scored.append(
                {
                    **chunk,
                    "score": score,
                }
            )

    scored.sort(
        key=lambda chunk: (
            chunk["score"],
            chunk["document_updated_at"],
            -chunk["chunk_index"],
        ),
        reverse=True,
    )
    return scored[:top_k], scored, tokens, phrase_queries


def _serialize_retrieved_chunks(chunks: list[dict]) -> list[dict]:
    return [
        {
            "id": chunk["id"],
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "chunk_index": chunk["chunk_index"],
            "score": chunk["score"],
            "preview": preview_text(chunk["content"], 220),
            "content": chunk["content"],
            "metadata": chunk["metadata"],
        }
        for chunk in chunks
    ]


def _normalize_answer(output: str) -> str:
    cleaned = output.strip()
    if not cleaned:
        return "I don't know."

    lowered = cleaned.lower()
    if lowered.startswith("i don't know") or lowered.startswith("i do not know"):
        return "I don't know."

    return cleaned


@router.post("/query")
async def query_docs(request: QueryRequest):
    trace_id = uuid.uuid4().hex[:12]
    start = perf_counter()

    try:
        query = request.query.strip()
        if not query:
            return {"answer": "I don't know.", "sources": [], "trace_id": trace_id}

        log_trace_event(
            "query.received",
            {
                "query": query,
                "provider": LLM_PROVIDER,
                "model": LLM_MODEL,
            },
            trace_id=trace_id,
        )

        entity, enforce_entity = _extract_entity(query)
        top_chunks, all_scored_chunks, tokens, phrase_queries = _retrieve_chunks(query, top_k=TOP_K)

        log_trace_event(
            "query.retrieved",
            {
                "query": query,
                "candidate_count": len(all_scored_chunks),
                "selected_count": len(top_chunks),
                "top_chunks": _serialize_retrieved_chunks(top_chunks),
            },
            trace_id=trace_id,
        )

        if not top_chunks:
            answer = "I don't know."
            log_query_event(
                {
                    "trace_id": trace_id,
                    "query": query,
                    "phrase_queries": phrase_queries,
                    "top_k": TOP_K,
                    "entity": entity,
                    "entity_in_context": False,
                    "context": "",
                    "retrieved": [],
                    "answer": answer,
                    "abstained": True,
                    "provider": LLM_PROVIDER,
                    "model": LLM_MODEL,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                }
            )
            return {"answer": answer, "sources": [], "trace_id": trace_id}

        context_chunks = top_chunks[:MAX_CONTEXT_CHUNKS]
        context = "\n\n".join(chunk["content"] for chunk in context_chunks)
        entity_in_context = True
        if entity and enforce_entity:
            entity_in_context = entity.lower() in context.lower()
            if not entity_in_context:
                answer = "I don't know."
                log_trace_event(
                    "query.entity_miss",
                    {
                        "query": query,
                        "entity": entity,
                    },
                    trace_id=trace_id,
                )
                log_query_event(
                    {
                        "trace_id": trace_id,
                        "query": query,
                        "phrase_queries": phrase_queries,
                        "top_k": TOP_K,
                        "entity": entity,
                        "entity_enforced": enforce_entity,
                        "entity_in_context": False,
                        "context": context,
                        "retrieved": _serialize_retrieved_chunks(top_chunks),
                        "answer": answer,
                        "abstained": True,
                        "provider": LLM_PROVIDER,
                        "model": LLM_MODEL,
                        "duration_ms": round((perf_counter() - start) * 1000, 2),
                    }
                )
                return {"answer": answer, "sources": [], "trace_id": trace_id}

        role_hit = None
        if tokens & WORK_INTENT_TERMS and entity:
            role_hit = _extract_role_for_org(context, entity)
            if role_hit:
                output = f"{role_hit}, {entity}"
                sources = [
                    {
                        "document_id": chunk["document_id"],
                        "filename": chunk["filename"],
                        "chunk_index": chunk["chunk_index"],
                        "score": chunk["score"],
                        "preview": chunk["preview"],
                    }
                    for chunk in top_chunks
                ]
                log_trace_event(
                    "query.rule_hit",
                    {
                        "query": query,
                        "rule": "role_for_org",
                        "answer": output,
                    },
                    trace_id=trace_id,
                )
                log_query_event(
                    {
                        "trace_id": trace_id,
                        "query": query,
                        "phrase_queries": phrase_queries,
                        "top_k": TOP_K,
                        "entity": entity,
                        "entity_enforced": enforce_entity,
                        "entity_in_context": entity_in_context,
                        "context": context,
                        "retrieved": _serialize_retrieved_chunks(top_chunks),
                        "answer": output,
                        "abstained": False,
                        "provider": LLM_PROVIDER,
                        "model": LLM_MODEL,
                        "rule_hit": "role_for_org",
                        "duration_ms": round((perf_counter() - start) * 1000, 2),
                    }
                )
                return {"answer": output, "sources": sources, "trace_id": trace_id}

        subject_hint = _infer_subject_from_sources(top_chunks) or _infer_subject_from_context(context)
        subject_line = ""
        if subject_hint:
            subject_line = (
                f"The document is about {subject_hint}. "
                "All experience and skills refer to this person unless explicitly stated otherwise."
            )

        prompt = f"""You are a helpful assistant for a personal knowledge base.
Answer the question using the provided context only.
If the context is insufficient, say "I don't know."
{subject_line}
Context:
{context}

Question:
{query}

Answer:
"""

        log_trace_event(
            "query.prompt_built",
            {
                "query": query,
                "context_chars": len(context),
                "context_chunk_count": len(context_chunks),
                "prompt_preview": preview_text(prompt, 600),
            },
            trace_id=trace_id,
        )

        output, llm_duration_ms = generate_text(prompt)
        output = _normalize_answer(output)

        log_trace_event(
            "query.llm_response",
            {
                "query": query,
                "provider": LLM_PROVIDER,
                "model": LLM_MODEL,
                "duration_ms": llm_duration_ms,
                "answer_preview": preview_text(output, 400),
            },
            trace_id=trace_id,
        )

        sources = [
            {
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "score": chunk["score"],
                "preview": chunk["preview"],
            }
            for chunk in top_chunks
        ]

        total_duration_ms = round((perf_counter() - start) * 1000, 2)
        log_query_event(
            {
                "trace_id": trace_id,
                "query": query,
                "phrase_queries": phrase_queries,
                "top_k": TOP_K,
                "entity": entity,
                "entity_enforced": enforce_entity,
                "entity_in_context": entity_in_context,
                "context": context,
                "retrieved": _serialize_retrieved_chunks(top_chunks),
                "answer": output,
                "abstained": output == "I don't know.",
                "provider": LLM_PROVIDER,
                "model": LLM_MODEL,
                "llm_duration_ms": llm_duration_ms,
                "duration_ms": total_duration_ms,
            }
        )
        logger.info(
            "Answered trace_id=%s duration_ms=%s chunks=%s query=%s",
            trace_id,
            total_duration_ms,
            len(top_chunks),
            query,
        )
        return {"answer": output, "sources": sources, "trace_id": trace_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Query failed trace_id=%s", trace_id)
        raise HTTPException(status_code=500, detail=str(exc))
