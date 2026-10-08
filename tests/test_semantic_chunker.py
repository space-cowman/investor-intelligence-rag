from ingestion.semantic_chunker import PICTURE_PLACEHOLDER, chunk_markdown


def write_markdown(tmp_path, text):
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_splits_on_headers(tmp_path):
    text = "# Title\n\nIntro text.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"
    chunks = chunk_markdown(write_markdown(tmp_path, text))
    assert len(chunks) >= 2


def test_respects_chunk_size(tmp_path):
    paragraph = "This is a sentence that repeats to build up length. " * 200
    text = f"# Title\n\n{paragraph}"
    chunks = chunk_markdown(write_markdown(tmp_path, text), chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.page_content) <= 500 + 200  # splitter can overshoot slightly at natural breaks


def test_removes_picture_placeholder(tmp_path):
    text = "# Title\n\nBefore.\n\n**==> picture of a chart intentionally omitted <==**\n\nAfter."
    chunks = chunk_markdown(write_markdown(tmp_path, text))
    combined = "\n".join(c.page_content for c in chunks)
    assert "picture" not in combined.lower()
    assert "Before." in combined
    assert "After." in combined


def test_picture_placeholder_regex_matches_expected_format():
    sample = "**==> picture of a bar chart intentionally omitted <==**"
    assert PICTURE_PLACEHOLDER.search(sample)


def test_small_document_produces_one_chunk(tmp_path):
    text = "# Title\n\nShort content."
    chunks = chunk_markdown(write_markdown(tmp_path, text))
    assert len(chunks) == 1
    assert "Short content." in chunks[0].page_content
