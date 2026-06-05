import json
import sqlite3
import uuid
from pathlib import Path

from app.config import STORE_DB_PATH
from app.core.rag_logger import preview_text, utcnow_iso


class DocumentStore:
    def __init__(self, db_path: str = STORE_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    source_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                ON chunks(document_id, chunk_index);
                """
            )

    def upsert_document(
        self,
        *,
        file_path: str,
        content_hash: str,
        file_size: int,
        chunks,
    ) -> dict:
        filename = Path(file_path).name
        now = utcnow_iso()
        normalized_chunks = []
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata or {})
            metadata.update(
                {
                    "source": filename,
                    "chunk_index": index,
                }
            )
            normalized_chunks.append(
                {
                    "chunk_index": index,
                    "content": chunk.page_content,
                    "preview": preview_text(chunk.page_content, 220),
                    "metadata_json": json.dumps(metadata),
                    "char_count": len(chunk.page_content),
                }
            )

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM documents WHERE filename = ?",
                (filename,),
            ).fetchone()

            if existing and existing["content_hash"] == content_hash:
                connection.execute(
                    """
                    UPDATE documents
                    SET source_path = ?, file_size = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (file_path, file_size, now, existing["id"]),
                )
                document = self.get_document(existing["id"])
                return {
                    "document": document,
                    "status": "unchanged",
                }

            document_id = existing["id"] if existing else uuid.uuid4().hex

            if existing:
                connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                connection.execute(
                    """
                    UPDATE documents
                    SET source_path = ?, content_hash = ?, file_size = ?, chunk_count = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (file_path, content_hash, file_size, len(normalized_chunks), now, document_id),
                )
                status = "reindexed"
            else:
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, filename, source_path, content_hash, file_size,
                        chunk_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        filename,
                        file_path,
                        content_hash,
                        file_size,
                        len(normalized_chunks),
                        now,
                        now,
                    ),
                )
                status = "indexed"

            for chunk in normalized_chunks:
                chunk_id = f"{document_id}:{chunk['chunk_index']}"
                connection.execute(
                    """
                    INSERT INTO chunks (
                        id, document_id, chunk_index, content, preview,
                        metadata_json, char_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        chunk["chunk_index"],
                        chunk["content"],
                        chunk["preview"],
                        chunk["metadata_json"],
                        chunk["char_count"],
                        now,
                    ),
                )

            document = self.get_document(document_id, connection)
            return {
                "document": document,
                "status": status,
            }

    def get_document(self, document_id: str, connection: sqlite3.Connection | None = None) -> dict | None:
        should_close = connection is None
        if connection is None:
            connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            return self._row_to_document(row) if row else None
        finally:
            if should_close:
                connection.close()

    def list_documents(self, limit: int = 100) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM documents
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_document(row) for row in rows]

    def list_chunks(self, limit: int | None = None) -> list[dict]:
        with self._connect() as connection:
            query = """
                SELECT
                    chunks.id,
                    chunks.document_id,
                    chunks.chunk_index,
                    chunks.content,
                    chunks.preview,
                    chunks.metadata_json,
                    chunks.char_count,
                    documents.filename,
                    documents.updated_at AS document_updated_at
                FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                ORDER BY documents.updated_at DESC, chunks.chunk_index ASC
            """
            params: tuple = ()
            if limit is not None:
                query += " LIMIT ?"
                params = (limit,)
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def get_document_chunks(self, document_id: str, limit: int = 200) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    chunks.id,
                    chunks.document_id,
                    chunks.chunk_index,
                    chunks.content,
                    chunks.preview,
                    chunks.metadata_json,
                    chunks.char_count,
                    documents.filename,
                    documents.updated_at AS document_updated_at
                FROM chunks
                JOIN documents ON documents.id = chunks.document_id
                WHERE chunks.document_id = ?
                ORDER BY chunks.chunk_index ASC
                LIMIT ?
                """,
                (document_id, limit),
            ).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def count_documents(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM documents").fetchone()
            return int(row["total"])

    def count_chunks(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM chunks").fetchone()
            return int(row["total"])

    def _row_to_document(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "filename": row["filename"],
            "source_path": row["source_path"],
            "content_hash": row["content_hash"],
            "file_size": row["file_size"],
            "chunk_count": row["chunk_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_chunk(self, row: sqlite3.Row) -> dict:
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return {
            "id": row["id"],
            "document_id": row["document_id"],
            "filename": row["filename"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "preview": row["preview"],
            "char_count": row["char_count"],
            "metadata": metadata,
            "document_updated_at": row["document_updated_at"],
        }


_STORE: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    global _STORE
    if _STORE is None:
        _STORE = DocumentStore()
    return _STORE
