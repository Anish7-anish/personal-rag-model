# personal-rag-model
Personal RAG app: upload documents and ask questions about yourself.

## Quickstart
Backend (FastAPI + Chroma + Ollama):
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

## Configuration
- `OLLAMA_MODEL`: defaults to `llama3`. Set in `.env` or your shell.
- `VITE_API_BASE_URL`: defaults to `http://localhost:8000/api` for the frontend.

## RAG Monitoring
- Logs: `backend/data/logs/rag_queries.jsonl` (one JSON entry per query).
- Each entry includes query, retrieved chunks with scores, model answer, and abstention flag.

## Evaluation (Heuristics)
1) Create an eval file like `backend/evals/sample_eval.csv`.
2) Run:
```bash
python backend/scripts/eval_rag.py \
  --eval backend/evals/sample_eval.csv \
  --logs backend/data/logs/rag_queries.jsonl
```
This reports heuristics for faithfulness, context precision/recall, answer accuracy, and abstention quality.
