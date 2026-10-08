import os
from pathlib import Path

from dotenv import load_dotenv

from ingestion.embeddings import get_embeddings
from ingestion.semantic_chunker import chunk_markdown
from vectorstore.opensearch_store import OpenSearchVectorStore, Retriever

load_dotenv()

MARKDOWN_FILE = Path("data/markdown/2024_Apple.md")
COMPANY, YEAR, SOURCE_FILE = "Apple", "2024", "2024_Apple.pdf"
QUESTION = "What was Apple's total net sales?"


def main() -> None:
    if not MARKDOWN_FILE.exists():
        raise FileNotFoundError(f"{MARKDOWN_FILE} not found. Run: python -m ingestion.pdf_to_markdown")

    embeddings = get_embeddings()

    store = OpenSearchVectorStore(
        endpoint=os.environ["OPENSEARCH_ENDPOINT"],
        index_name=os.getenv("OPENSEARCH_INDEX_NAME", "investor-docs"),
        region=os.getenv("AWS_REGION", "us-east-1"),
        service=os.getenv("OPENSEARCH_SERVICE", "es"),
    )

    chunks = chunk_markdown(str(MARKDOWN_FILE))
    print(f"Uploading {len(chunks)} chunks...")
    store.upload_chunks(chunks, embeddings, company=COMPANY, year=YEAR, source_file=SOURCE_FILE)
    print(f"Documents in '{store.index_name}': {store.client.count(index=store.index_name)['count']}")

    results = Retriever(store.client, store.index_name, embeddings).search(
        QUESTION, company=COMPANY, year=YEAR, k=3
    )
    print(f"\nQuestion: {QUESTION}")
    for doc in results:
        print("-" * 80)
        print(f"score={doc.metadata['score']:.3f}  chunk_id={doc.metadata['chunk_id']}")
        print(doc.page_content[:500])


if __name__ == "__main__":
    main()