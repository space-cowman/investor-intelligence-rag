from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf4llm


class PDFToMarkdownConverter:
    """Convert PDF documents to Markdown."""

    def _convert(self, pdf_path: str, output_dir: str, force: bool = False) -> tuple[str, str]:
        """Return (markdown_path, status) where status is 'converted' or 'skipped'."""
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        markdown_file = Path(output_dir) / f"{pdf_file.stem}.md"

        if not force and markdown_file.exists() and markdown_file.stat().st_mtime >= pdf_file.stat().st_mtime:
            return str(markdown_file), "skipped"

        markdown_file.parent.mkdir(parents=True, exist_ok=True)
        markdown_file.write_text(pymupdf4llm.to_markdown(str(pdf_file)), encoding="utf-8")
        return str(markdown_file), "converted"

    def convert_pdf(self, pdf_path: str, output_dir: str, force: bool = False) -> str:
        """Convert one PDF; prints status and returns the .md path."""
        path, status = self._convert(pdf_path, output_dir, force)
        label = "Skipped (already up to date)" if status == "skipped" else "Converted"
        print(f"  {label}: {Path(pdf_path).name} -> {path}")
        return path

    def convert_directory(self, input_dir: str, output_dir: str,
                          workers: int = 4, force: bool = False) -> list[str]:
        """Convert all PDFs in a folder in parallel."""
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise FileNotFoundError(f"Input folder not found: {input_path}")

        pdfs = sorted(p for p in input_path.iterdir() if p.suffix.lower() == ".pdf")
        if not pdfs:
            print(f"No PDFs found in {input_path}")
            return []

        results, converted, skipped, failed = [], 0, 0, 0
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._convert, str(p), output_dir, force): p for p in pdfs}
            for future, pdf in futures.items():
                try:
                    path, status = future.result()
                    results.append(path)
                    if status == "skipped":
                        skipped += 1
                        print(f"  Skipped (already up to date): {pdf.name}")
                    else:
                        converted += 1
                        print(f"  Converted: {pdf.name}")
                except Exception as e:
                    failed += 1
                    print(f"  ! Failed {pdf.name}: {e}")

        print(f"\nDone: {converted} converted, {skipped} skipped, {failed} failed")
        return results


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[1]   # file lives in <repo>/ingestion/
    PDFToMarkdownConverter().convert_directory(
        str(repo_root / "data" / "raw_pdfs"),
        str(repo_root / "data" / "markdown"),
        force="--force" in sys.argv,
    )