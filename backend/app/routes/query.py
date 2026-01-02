# backend/app/routes/query.py

import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from app.core.vectorstore import get_vectorstore
from app.core.rag_logger import log_query_event
from app.config import OLLAMA_MODEL

router = APIRouter()

class QueryRequest(BaseModel):
    query: str


TOP_K = 15
MMR_FETCH_K = 50
WORK_INTENT_TERMS = {"role", "work", "worked", "working", "job", "position", "employment", "experience"}


def _extract_entity(query: str):
    match = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", query)
    if match:
        return match[0], True
    if "anish" in query.lower():
        return "Anish", False
    return None, False


def _infer_subject_from_sources(docs):
    sources = []
    for doc in docs:
        metadata = doc.metadata or {}
        source = metadata.get("source")
        if source:
            sources.append(source)
    if not sources:
        return None
    filenames = {Path(source).stem for source in sources}
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


def _doc_key(doc):
    metadata = doc.metadata or {}
    return (
        metadata.get("source"),
        metadata.get("page"),
        metadata.get("section"),
        doc.page_content[:200],
    )


def _lexical_score(doc, tokens, phrase_queries):
    text = doc.page_content.lower()
    score = 0
    for phrase in phrase_queries:
        if phrase.lower() in text:
            score += 10
    for token in tokens:
        if token in text:
            score += 1
    return score


def _extract_role_for_org(context: str, org: str):
    if not org:
        return None
    escaped = re.escape(org)
    pattern = re.compile(rf"([A-Z][A-Za-z &/]+),\s*{escaped}", re.IGNORECASE)
    match = pattern.search(context)
    if match:
        return match.group(1).strip()
    return None


@router.post("/query")
async def query_docs(request: QueryRequest):
    """
    Retrieve top-k relevant chunks from Chroma and query Ollama model.
    """
    try:
        query = request.query.strip()
        if not query:
            return {"answer": "I don't know.", "sources": []}

        entity, enforce_entity = _extract_entity(query)
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        retrieval_query = query
        if tokens & WORK_INTENT_TERMS:
            retrieval_query = f"{query} experience"
        phrase_queries = _extract_phrases(query)
        expanded_phrase_queries = _expand_phrase_queries(phrase_queries, tokens)
        # Get stored embeddings
        db = get_vectorstore()
        try:
            docs = db.max_marginal_relevance_search(
                retrieval_query, k=TOP_K, fetch_k=MMR_FETCH_K
            )
            pairs = [(doc, None) for doc in docs]
        except AttributeError:
            try:
                results = db.similarity_search_with_relevance_scores(
                    retrieval_query, k=TOP_K
                )
                pairs = [(doc, score) for doc, score in results]
            except AttributeError:
                pairs = [
                    (doc, None)
                    for doc in db.similarity_search(retrieval_query, k=TOP_K)
                ]

        if expanded_phrase_queries:
            extra_pairs = []
            for phrase in expanded_phrase_queries:
                try:
                    phrase_docs = db.similarity_search(phrase, k=3)
                except AttributeError:
                    phrase_docs = []
                extra_pairs.extend([(doc, None) for doc in phrase_docs])
            pairs.extend(extra_pairs)

        pairs = [
            (doc, score)
            for doc, score in pairs
            if doc.page_content and doc.page_content.strip()
        ]
        unique_pairs = {}
        for doc, score in pairs:
            key = _doc_key(doc)
            if key not in unique_pairs:
                unique_pairs[key] = (doc, score)
        docs = [doc for doc, _ in unique_pairs.values()]
        scores = [score for _, score in unique_pairs.values()]

        docs = sorted(
            docs,
            key=lambda doc: _lexical_score(doc, tokens, expanded_phrase_queries),
            reverse=True,
        )[:TOP_K]
        if not docs:
            log_query_event(
                {
                    "query": query,
                    "retrieval_query": retrieval_query,
                    "phrase_queries": expanded_phrase_queries,
                    "top_k": TOP_K,
                    "entity": entity,
                    "entity_in_context": False,
                    "context": "",
                    "retrieved": [],
                    "answer": "I don't know.",
                    "abstained": True,
                    "model": OLLAMA_MODEL,
                }
            )
            return {"answer": "I don't know.", "sources": []}

        # Combine context text
        context = "\n\n".join([d.page_content for d in docs])
        entity_in_context = True
        if entity and enforce_entity:
            entity_in_context = entity.lower() in context.lower()
            if not entity_in_context:
                log_query_event(
                    {
                        "query": query,
                        "retrieval_query": retrieval_query,
                        "phrase_queries": expanded_phrase_queries,
                        "top_k": TOP_K,
                        "entity": entity,
                        "entity_enforced": enforce_entity,
                        "entity_in_context": False,
                        "context": context,
                        "retrieved": [
                            {
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "score": score,
                            }
                            for doc, score in zip(docs, scores)
                        ],
                        "answer": "I don't know.",
                        "abstained": True,
                        "model": OLLAMA_MODEL,
                    }
                )
                return {"answer": "I don't know.", "sources": []}

        role_hit = None
        if tokens & WORK_INTENT_TERMS and entity:
            role_hit = _extract_role_for_org(context, entity)
            if role_hit:
                output = f"{role_hit}, {entity}"
                sources = []
                seen_sources = set()
                for doc in docs:
                    metadata = doc.metadata or {}
                    source = metadata.get("source")
                    if source and source not in seen_sources:
                        sources.append(metadata)
                        seen_sources.add(source)
                    elif not source:
                        sources.append(metadata)
                log_query_event(
                    {
                        "query": query,
                        "retrieval_query": retrieval_query,
                        "phrase_queries": expanded_phrase_queries,
                        "top_k": TOP_K,
                        "entity": entity,
                        "entity_enforced": enforce_entity,
                        "entity_in_context": entity_in_context,
                        "context": context,
                        "retrieved": [
                            {
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "score": score,
                            }
                            for doc, score in zip(docs, scores)
                        ],
                        "answer": output,
                        "abstained": False,
                        "model": OLLAMA_MODEL,
                        "rule_hit": "role_for_org",
                    }
                )
                return {"answer": output, "sources": sources}

        subject_hint = _infer_subject_from_sources(docs) or _infer_subject_from_context(context)
        subject_line = ""
        if subject_hint:
            subject_line = (
                f"The document is the resume of {subject_hint}. "
                "All experience and skills refer to this person unless explicitly stated otherwise."
            )

        # Prepare the prompt
        prompt = f"""You are a helpful assistant.
Answer the question using the following context only.
If you don't know, say you don't know.
{subject_line}
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

        try:
            payload = response.json()
            output = payload.get("response", "")
        except ValueError:
            # Ollama may return newline-delimited JSON; aggregate response chunks.
            lines = [line for line in response.text.splitlines() if line.strip()]
            if not lines:
                raise HTTPException(status_code=500, detail="Empty response from Ollama API")
            output_parts = []
            for line in lines:
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "response" in chunk:
                    output_parts.append(chunk["response"])
            if not output_parts:
                raise HTTPException(status_code=500, detail="Invalid JSON from Ollama API")
            output = "".join(output_parts)

        output = output.strip() or "I don't know."
        sources = []
        seen_sources = set()
        for doc in docs:
            metadata = doc.metadata or {}
            source = metadata.get("source")
            if source and source not in seen_sources:
                sources.append(metadata)
                seen_sources.add(source)
            elif not source:
                sources.append(metadata)
        log_query_event(
            {
                "query": query,
                "retrieval_query": retrieval_query,
                "phrase_queries": expanded_phrase_queries,
                "top_k": TOP_K,
                "entity": entity,
                "entity_enforced": enforce_entity,
                "entity_in_context": entity_in_context,
                "context": context,
                "retrieved": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score,
                    }
                    for doc, score in zip(docs, scores)
                ],
                "answer": output,
                "abstained": output == "I don't know.",
                "model": OLLAMA_MODEL,
            }
        )
        return {"answer": output, "sources": sources}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
