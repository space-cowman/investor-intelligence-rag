from pathlib import Path

from ingestion.ingest_documents import parse_company_year


def test_year_company_format():
    company, year = parse_company_year(Path("2024_Apple.pdf"))
    assert company == "Apple"
    assert year == "2024"


def test_year_annualreport_company_format():
    company, year = parse_company_year(Path("2024_AnnualReport_Apple.pdf"))
    assert company == "Apple"
    assert year == "2024"


def test_company_year_format_fallback():
    company, year = parse_company_year(Path("Apple_2024.pdf"))
    assert company == "Apple"
    assert year == "2024"


def test_single_word_filename():
    company, year = parse_company_year(Path("Apple.pdf"))
    assert company == "Apple"
    assert year == ""
