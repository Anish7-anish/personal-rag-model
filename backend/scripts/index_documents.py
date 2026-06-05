import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.document_store import get_document_store
from app.core.utils import compute_file_hash, load_and_split


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".doc", ".docx"}


def iter_files(paths: list[str], recursive: bool):
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path
            continue

        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            for child in iterator:
                if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES:
                    yield child


def main():
    parser = argparse.ArgumentParser(
        description="Index local files into the personal RAG corpus."
    )
    parser.add_argument("paths", nargs="+", help="File or directory paths to index.")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directory paths.",
    )
    args = parser.parse_args()

    store = get_document_store()
    indexed = 0
    for file_path in iter_files(args.paths, recursive=args.recursive):
        chunks = load_and_split(str(file_path))
        result = store.upsert_document(
            file_path=str(file_path),
            content_hash=compute_file_hash(str(file_path)),
            file_size=file_path.stat().st_size,
            chunks=chunks,
        )
        document = result["document"]
        indexed += 1
        print(
            f"{result['status']}: {document['filename']} "
            f"({document['chunk_count']} chunks, id={document['id']})"
        )

    if indexed == 0:
        print("No supported files found.")


if __name__ == "__main__":
    main()
