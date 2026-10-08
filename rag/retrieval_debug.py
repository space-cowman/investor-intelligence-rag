import argparse
import os

from dotenv import load_dotenv

from ingestion.embeddings import get_embeddings
from vectorstore.opensearch_store import OpenSearchVectorStore, Retriever

load_dotenv()


def search_vectorstore(query: str, company: str | None, year: str | None, k: int):
    store = OpenSearchVectorStore(
        endpoint=os.environ["OPENSEARCH_ENDPOINT"],
        index_name=os.getenv("OPENSEARCH_INDEX_NAME", "investor-docs"),
        region=os.getenv("AWS_REGION", "us-east-1"),
        service=os.getenv("OPENSEARCH_SERVICE", "es"),
    )
    results = Retriever(store.client, store.index_name, get_embeddings()).search(
        query, company=company, year=year, k=k
    )

    print(f"Query: {query!r} | company={company} year={year} k={k}")
    print(f"Results: {len(results)}\n")

    for idx, doc in enumerate(results, start=1):
        m = doc.metadata
        snippet = doc.page_content.strip().replace("\n", " ")
        snippet = snippet[:350].rstrip() + "..." if len(snippet) > 350 else snippet
        print(f"Result {idx}  score={m['score']:.3f}  {m['company']} {m['year']}  chunk={m['chunk_id']}")
        print(f"  {snippet}\n  " + "-" * 60)

    if not results:
        print("No results. Check the index contents or try a different query.")
    return results


def main():
    parser = argparse.ArgumentParser(description="Debug OpenSearch retrieval")
    parser.add_argument("query", nargs="+", help="search text")
    parser.add_argument("--company")
    parser.add_argument("--year")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    search_vectorstore(" ".join(args.query), args.company, args.year, args.k)


if __name__ == "__main__":
    main()