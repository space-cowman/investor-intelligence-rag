from rag.kpi_extractor_rag import FinancialMetrics


def test_null_like_strings_become_none():
    for value in ["null", "Null", "N/A", "n/a", "none", "not available", "unavailable", "not found", "", "  "]:
        m = FinancialMetrics(revenue=value)
        assert m.revenue is None, f"{value!r} should become None"


def test_real_value_passes_through():
    m = FinancialMetrics(revenue="$391,035 million")
    assert m.revenue == "$391,035 million"


def test_numeric_value_is_stringified():
    m = FinancialMetrics(revenue=391035)
    assert m.revenue == "391035"


def test_list_filters_out_null_entries_only():
    m = FinancialMetrics(risk_factors=["Macroeconomic conditions", "null", "N/A", "Tax uncertainties"])
    assert m.risk_factors == ["Macroeconomic conditions", "Tax uncertainties"]


def test_all_null_list_becomes_none():
    m = FinancialMetrics(growth_drivers=["null", "n/a", ""])
    assert m.growth_drivers is None


def test_empty_list_becomes_none():
    m = FinancialMetrics(growth_drivers=[])
    assert m.growth_drivers is None


def test_default_fields_are_none():
    m = FinancialMetrics()
    assert m.revenue is None
    assert m.risk_factors is None
