# personal-rag-model
Personal RAG app: build a persistent corpus about yourself, then query it locally with Ollama.

## Quickstart
Backend (FastAPI + local SQLite corpus store + Ollama):
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OLLAMA_MODEL=llama3
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
- `OLLAMA_MODEL`: defaults to `llama3`. Set in `.env` or your shell.
- `OLLAMA_BASE_URL`: defaults to `http://127.0.0.1:11434`.
- `OLLAMA_TIMEOUT_SECONDS`: defaults to `120`.
- `LOG_LEVEL`: defaults to `INFO`.
- `VITE_API_BASE_URL`: defaults to `http://localhost:8000/api` for the frontend.

## How It Works
- Uploaded files are stored in `backend/data/uploads/`.
- Parsed chunks and document metadata are persisted in `backend/data/rag_store.sqlite3`.
- The corpus survives backend restarts.
- Ollama is used only for final answer generation; retrieval is local and does not require downloading embedding models.

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
