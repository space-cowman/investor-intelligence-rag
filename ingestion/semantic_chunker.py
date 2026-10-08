import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
PICTURE_PLACEHOLDER = re.compile(r"\*\*==> picture .*? intentionally omitted <==\*\*")


def read_markdown(markdown_file: str) -> str:
    return Path(markdown_file).read_text(encoding="utf-8")


def chunk_markdown(markdown_file: str, embeddings=None,
                   chunk_size: int = 3000, chunk_overlap: int = 400) -> list[Document]:
    """Split by Markdown headings, then cap each piece at chunk_size characters.

    `embeddings` is unused; kept so callers don't need changes.
    chunk_size=3000 (was 1500): financial statement tables run ~1800-2600 chars
    and were getting split mid-table, separating figures from their labels.
    """
    text = PICTURE_PLACEHOLDER.sub("", read_markdown(markdown_file))

    sections = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS, strip_headers=False
    ).split_text(text)

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(sections)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    markdown_file = repo_root / "data" / "markdown" / "2024_Apple.md"

    chunks = chunk_markdown(str(markdown_file))
    sizes = [len(c.page_content) for c in chunks]

    print(f"Generated {len(chunks)} chunks")
    print(f"Chars per chunk -> min {min(sizes)}, avg {sum(sizes)//len(sizes)}, max {max(sizes)}\n")

    for i, chunk in enumerate(chunks[:3], start=1):
        print("=" * 80, f"\nChunk {i}  |  metadata: {chunk.metadata}\n", "=" * 80, sep="")
        print(chunk.page_content[:1000], "\n")