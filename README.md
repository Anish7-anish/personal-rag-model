# personal-rag-model
Personal RAG app: build a persistent corpus about yourself, then query it with local retrieval and either Groq or Ollama for final answer generation.

## Current Status
- Persistent local corpus storage is working through `backend/data/rag_store.sqlite3`.
- Uploads can come from the frontend or from the CLI indexing script.
- Retrieval runs locally in the backend against the stored corpus.
- Final answer generation works with Groq free tier and can fall back to Ollama.
- Query traces and logs are written to `backend/data/logs/`.
- The frontend can list indexed documents without exposing chunk text in the UI.

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

Test one real query:
```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Who is Anish?"}'
```

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
- Upload chunk previews are logged in the backend console during indexing.

Useful debug endpoints:
- `GET /api/debug/query-logs`
- `GET /api/debug/traces`

Each query response also returns a `trace_id` so you can match UI behavior to the trace log.

## Secrets And Env Files
- Commit `backend/.env.example`, not the real `backend/.env`.
- Keep `GROQ_API_KEY` in `backend/.env` locally and in your deployment provider's secret manager in production.
- Do not put backend secrets in the frontend. `VITE_*` variables are public to the browser.
- If a secret is ever committed accidentally, rotate it immediately and replace it with a new key.

Local backend example:
```env
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=your_real_groq_api_key_here
```

Frontend example:
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Portfolio Deployment Checklist
Before connecting this to a public portfolio:
- Add backend rate limiting so anonymous users cannot burn the Groq free tier.
- Tighten CORS to your deployed portfolio domain instead of `*`.
- Deploy the backend separately and set `VITE_API_BASE_URL` in the frontend to that hosted backend URL.
- Keep `backend/data/uploads/` and `backend/data/rag_store.sqlite3` on persistent storage on the backend host.
- Keep `GROQ_API_KEY` only on the backend host, never in the frontend bundle.

Recommended order:
1. Add rate limiting.
2. Restrict CORS.
3. Deploy the backend with persistent storage.
4. Point the portfolio frontend to the deployed backend.
5. Re-test upload, query, logs, and document persistence after deployment.

## Evaluation
1) Create an eval file like `backend/evals/sample_eval.csv`.
2) Run:
```bash
python backend/scripts/eval_rag.py \
  --eval backend/evals/sample_eval.csv \
  --logs backend/data/logs/rag_queries.jsonl
```
This reports heuristics for faithfulness, context precision/recall, answer accuracy, and abstention quality.
