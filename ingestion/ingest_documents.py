import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from ingestion.embeddings import get_embeddings
from ingestion.pdf_to_markdown import PDFToMarkdownConverter
from ingestion.semantic_chunker import chunk_markdown
from vectorstore.opensearch_store import OpenSearchVectorStore, Retriever

load_dotenv()

# Optional stages: each runs only if its module exists.
try:
    from rag.kpi_extractor_rag import extract_financial_metrics
    KPI_ENABLED = True
except ImportError as e:
    print(f"KPI extraction disabled: {e}")
    KPI_ENABLED = False

try:
    from database.save_metrics import save_metrics
    DB_ENABLED = True
except ImportError as e:
    print(f"PostgreSQL saving disabled: {e}")
    DB_ENABLED = False


def parse_company_year(pdf_file: Path) -> tuple[str, str]:
    """Supports `2024_Apple.pdf` and `2024_AnnualReport_Apple.pdf`."""
    parts = pdf_file.stem.split("_")
    if parts and parts[0].isdigit():
        return parts[-1], parts[0]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return pdf_file.stem, ""


@lru_cache(maxsize=1)
def get_vector_store() -> OpenSearchVectorStore:
    """One shared OpenSearch client, built once per process instead of once per upload."""
    return OpenSearchVectorStore(
        endpoint=os.environ["OPENSEARCH_ENDPOINT"],
        index_name=os.getenv("OPENSEARCH_INDEX_NAME", "investor-docs"),
        region=os.getenv("AWS_REGION", "us-east-1"),
        service=os.getenv("OPENSEARCH_SERVICE", "es"),
    )


def ingest_document(pdf_path: str, embeddings, vector_store: OpenSearchVectorStore) -> None:
    pdf_file = Path(pdf_path)
    company, year = parse_company_year(pdf_file)
    print(f"\nIngesting {pdf_file.name} as company={company!r}, year={year!r}")

    # 1. PDF -> Markdown
    markdown_file = PDFToMarkdownConverter().convert_pdf(
        pdf_path=pdf_path, output_dir="data/markdown"
    )

    # 2. Markdown -> chunks
    chunks = chunk_markdown(markdown_file=markdown_file, embeddings=embeddings)
    print(f"Generated {len(chunks)} chunks for {pdf_file.name}")

    # 3. Chunks -> embeddings -> OpenSearch
    vector_store.upload_chunks(
        chunks=chunks, embeddings=embeddings,
        company=company, year=year, source_file=pdf_file.name,
    )

    # 4. KPI extraction (retrieve chunks -> LLM extracts numbers)
    if not KPI_ENABLED:
        return

    year_int = int(year) if year.isdigit() else None
    metrics = extract_financial_metrics(
        retriever=Retriever(vector_store.client, vector_store.index_name, embeddings),
        company=company,
        year=year_int,
    )
    print(f"Extracted KPIs: {metrics}")

    # 5. Save KPIs to PostgreSQL
    if DB_ENABLED and metrics:
        save_metrics(company=company, year=year_int, metrics=metrics)
        print("Saved KPIs to PostgreSQL")


def ingest_directory(input_dir: str) -> None:
    embeddings = get_embeddings()
    vector_store = get_vector_store()

    pdf_files = sorted(Path(input_dir).glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF(s) in {input_dir}")

    for pdf_file in pdf_files:
        ingest_document(str(pdf_file), embeddings, vector_store)


if __name__ == "__main__":
    ingest_directory("data/raw_pdfs")