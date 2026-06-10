import json
from time import perf_counter

import requests
from fastapi import HTTPException

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER, LLM_TIMEOUT_SECONDS


def _http_error(response: requests.Response, fallback: str) -> HTTPException:
    detail = fallback
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                detail = f"{fallback}: {message}"
        elif isinstance(error, str):
            detail = f"{fallback}: {error}"

    return HTTPException(status_code=500, detail=detail)


def _parse_openai_compatible_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise HTTPException(status_code=500, detail="Empty response from LLM provider")

    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return "".join(text_parts)
    return ""


def _generate_with_ollama(prompt: str) -> tuple[str, float]:
    started = perf_counter()
    response = requests.post(
        f"{LLM_BASE_URL.rstrip('/')}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=LLM_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise _http_error(response, f"Ollama returned status {response.status_code}")

    try:
        payload = response.json()
        output = payload.get("response", "")
    except ValueError:
        lines = [line for line in response.text.splitlines() if line.strip()]
        if not lines:
            raise HTTPException(status_code=500, detail="Empty response from Ollama API")
        output_parts = []
        for line in lines:
            try:
                chunk_payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "response" in chunk_payload:
                output_parts.append(chunk_payload["response"])
        if not output_parts:
            raise HTTPException(status_code=500, detail="Invalid JSON from Ollama API")
        output = "".join(output_parts)

    duration_ms = round((perf_counter() - started) * 1000, 2)
    return output, duration_ms


def _generate_with_groq(prompt: str) -> tuple[str, float]:
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured. Set it in backend/.env or your shell.",
        )

    started = perf_counter()
    response = requests.post(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise _http_error(response, f"Groq returned status {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid JSON from Groq API") from exc

    output = _parse_openai_compatible_content(payload)
    duration_ms = round((perf_counter() - started) * 1000, 2)
    return output, duration_ms


def generate_text(prompt: str) -> tuple[str, float]:
    if LLM_PROVIDER == "ollama":
        return _generate_with_ollama(prompt)
    if LLM_PROVIDER == "groq":
        return _generate_with_groq(prompt)

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. Expected 'groq' or 'ollama'.",
    )
