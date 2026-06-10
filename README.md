# personal-rag-model
Personal RAG app: build a persistent corpus about yourself, then query it with local retrieval and either Groq or Ollama for final answer generation.

## Quickstart
Backend (FastAPI + local SQLite corpus store + Groq free tier):
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# if backend/.env does not exist yet:
# cp .env.example .env
# otherwise edit backend/.env and add your real GROQ_API_KEY
uvicorn app.main:app --reload
```

Frontend (Vite + React):
```bash
cd frontend
npm install
npm run dev
```

Preview the production build:
```bash
cd frontend
npm run build
npm run preview
```

## Configuration
- `LLM_PROVIDER`: `groq` or `ollama`. If omitted, the backend auto-selects `groq` when `GROQ_API_KEY` is present and falls back to `ollama` otherwise.
- `LLM_MODEL`: optional explicit model override.
- `LLM_BASE_URL`: optional explicit base URL override.
- `LLM_TIMEOUT_SECONDS`: defaults to `120`.
- `GROQ_API_KEY`: required for Groq.
- `GROQ_MODEL`: defaults to `llama-3.1-8b-instant` for free-tier usage.
- `OLLAMA_MODEL`: defaults to `llama3` for local fallback.
- `OLLAMA_BASE_URL`: defaults to `http://127.0.0.1:11434`.
- `LOG_LEVEL`: defaults to `INFO`.
- `VITE_API_BASE_URL`: defaults to `http://localhost:8000/api` for the frontend.

## How It Works
- Uploaded files are stored in `backend/data/uploads/`.
- Parsed chunks and document metadata are persisted in `backend/data/rag_store.sqlite3`.
- The corpus survives backend restarts.
- Retrieval is local and does not require downloading embedding models.
- Final answer generation uses Groq when `GROQ_API_KEY` is configured, otherwise Ollama.

## Groq Free Tier
Recommended free-tier model:
- `llama-3.1-8b-instant`

You can switch to another Groq model by changing `LLM_MODEL` in `backend/.env`.

Example:
```bash
cd backend
# if needed: cp .env.example .env
# edit .env and paste your GROQ_API_KEY
uvicorn app.main:app --reload
```

Then verify the backend selected Groq:
```bash
curl http://127.0.0.1:8000/
```
You should see `llm_provider: groq` in the JSON response.

## Add Documents
From the UI:
- Use the upload form in the frontend.

From the command line:
```bash
cd backend
source venv/bin/activate
python scripts/index_documents.py data/uploads/Anish_AI_ML_Resume.pdf
python scripts/index_documents.py /absolute/path/to/folder --recursive
```

## Inspect The Corpus
- `GET /api/documents`: list indexed documents.
- `GET /api/documents/{document_id}/chunks`: inspect chunk text and metadata for one document.

Examples:
```bash
curl http://127.0.0.1:8000/api/documents
curl "http://127.0.0.1:8000/api/documents/<document_id>/chunks?limit=20"
```

## Logging And Debugging
- App log: `backend/data/logs/app.log`
- Query log: `backend/data/logs/rag_queries.jsonl`
- Trace log: `backend/data/logs/rag_trace.jsonl`

Useful debug endpoints:
- `GET /api/debug/query-logs`
- `GET /api/debug/traces`

Each query response also returns a `trace_id` so you can match UI behavior to the trace log.

## Evaluation
1) Create an eval file like `backend/evals/sample_eval.csv`.
2) Run:
```bash
python backend/scripts/eval_rag.py \
  --eval backend/evals/sample_eval.csv \
  --logs backend/data/logs/rag_queries.jsonl
```
This reports heuristics for faithfulness, context precision/recall, answer accuracy, and abstention quality.
