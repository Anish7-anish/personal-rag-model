import argparse
import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def normalize_tokens(text: str):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def load_logs(path: Path):
    entries = []
    if not path.exists():
        return entries
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def find_last_log(entries, query):
    for entry in reversed(entries):
        if entry.get("query") == query:
            return entry
    return None


def parse_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", required=True, help="Path to eval CSV file.")
    parser.add_argument("--logs", required=True, help="Path to rag_queries.jsonl.")
    args = parser.parse_args()

    logs = load_logs(Path(args.logs))

    results = []
    with open(args.eval, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            query = row.get("query", "").strip()
            expected_answer = row.get("expected_answer", "").strip()
            expected_keywords = parse_list(row.get("expected_keywords", ""))
            expected_sources = parse_list(row.get("expected_sources", ""))
            expected_abstain = row.get("expected_abstain", "").strip().lower() == "true"

            log_entry = find_last_log(logs, query)
            if not log_entry:
                results.append({"query": query, "error": "no log entry"})
                continue

            answer = log_entry.get("answer", "")
            retrieved = log_entry.get("retrieved", [])
            context = "\n".join(chunk.get("content", "") for chunk in retrieved)
            context_tokens = normalize_tokens(context)
            answer_tokens = normalize_tokens(answer)

            answer_similarity = similarity(answer, expected_answer)
            answer_correct = answer_similarity >= 0.75 if expected_answer else False

            relevant_chunks = 0
            for chunk in retrieved:
                content = chunk.get("content", "").lower()
                source = (chunk.get("metadata") or {}).get("source", "")
                if any(keyword.lower() in content for keyword in expected_keywords):
                    relevant_chunks += 1
                elif any(source.endswith(exp) or source == exp for exp in expected_sources):
                    relevant_chunks += 1

            retrieved_count = len(retrieved)
            context_precision = (
                relevant_chunks / retrieved_count if retrieved_count else 0.0
            )

            expected_relevant_total = len(expected_sources) or len(expected_keywords)
            context_recall = (
                relevant_chunks / expected_relevant_total
                if expected_relevant_total
                else None
            )

            token_overlap = (
                len(answer_tokens & context_tokens) / len(answer_tokens)
                if answer_tokens
                else 0.0
            )
            faithfulness = token_overlap >= 0.3 or answer == "I don't know."

            context_support = any(
                keyword.lower() in context.lower() for keyword in expected_keywords
            ) or (expected_answer and expected_answer.lower() in context.lower())

            abstained = answer == "I don't know."
            abstention_quality = (expected_abstain and abstained) or (
                not expected_abstain and not abstained
            )

            results.append(
                {
                    "query": query,
                    "answer": answer,
                    "answer_similarity": round(answer_similarity, 3),
                    "answer_correct": answer_correct,
                    "faithfulness": faithfulness,
                    "context_precision": round(context_precision, 3),
                    "context_recall": round(context_recall, 3)
                    if context_recall is not None
                    else None,
                    "context_support": context_support,
                    "abstention_quality": abstention_quality,
                }
            )

    if not results:
        print("No eval results.")
        return

    totals = {
        "answer_similarity": 0.0,
        "context_precision": 0.0,
        "faithfulness": 0.0,
        "context_support": 0.0,
        "abstention_quality": 0.0,
    }
    count = 0

    for result in results:
        if "error" in result:
            print(f"{result['query']}: {result['error']}")
            continue
        count += 1
        totals["answer_similarity"] += result["answer_similarity"]
        totals["context_precision"] += result["context_precision"]
        totals["faithfulness"] += 1 if result["faithfulness"] else 0
        totals["context_support"] += 1 if result["context_support"] else 0
        totals["abstention_quality"] += 1 if result["abstention_quality"] else 0

        print(
            f"{result['query']}: answer_similarity={result['answer_similarity']} "
            f"context_precision={result['context_precision']} "
            f"context_recall={result['context_recall']} "
            f"faithfulness={result['faithfulness']} "
            f"abstention_quality={result['abstention_quality']}"
        )

    if count:
        print("\nAggregate:")
        print(f"answer_similarity_avg={totals['answer_similarity'] / count:.3f}")
        print(f"context_precision_avg={totals['context_precision'] / count:.3f}")
        print(f"faithfulness_rate={totals['faithfulness'] / count:.3f}")
        print(f"context_support_rate={totals['context_support'] / count:.3f}")
        print(f"abstention_quality_rate={totals['abstention_quality'] / count:.3f}")


if __name__ == "__main__":
    main()
