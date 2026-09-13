"""AI Data Copilot extraction + input validation (Master Spec sections 12, 66)."""
import pytest

from app.engines.extraction import (AUTO_ACCEPT, extract_from_rows,
                                    extract_from_text)
from app.engines.knowledge_base import KnowledgeBaseError, load
from app.engines.models import ActivityRecord, FactoryContext

SAMPLE = ("We use around 480,000 kWh electricity per year, 26,000 litres of diesel "
          "and around 310 tonnes of silica sand for moulding. "
          "We send 240 tonnes of spent foundry sand to landfill every year and "
          "95 tonnes of metal scrap for recycling. "
          "Piped natural gas is about 96,000 m3 a year.")


def by_key(cands):
    return {c.key: c for c in cands}


def test_natural_language_extraction_reads_the_numbers_from_the_text():
    c = by_key(extract_from_text(SAMPLE))
    assert c["ELECTRICITY"].quantity == 480000
    assert c["ELECTRICITY"].unit == "kwh"
    assert c["DIESEL"].quantity == 26000
    assert c["NATURAL_GAS"].quantity == 96000


def test_material_function_is_captured_because_retrieval_depends_on_it():
    c = by_key(extract_from_text(SAMPLE))
    sand = c["SILICA_SAND"]
    assert sand.record_type == "MATERIAL"
    assert sand.function == "moulding"


def test_waste_treatment_route_is_captured():
    c = by_key(extract_from_text(SAMPLE))
    assert c["SPENT_FOUNDRY_SAND"].treatment == "LANDFILL"
    assert c["METAL_SCRAP"].treatment == "RECYCLED"


def test_clause_boundaries_stop_the_previous_noun_leaking_in():
    """'26,000 litres of diesel' must not be labelled electricity just because
    the previous clause mentioned electricity."""
    c = by_key(extract_from_text(SAMPLE))
    assert c["DIESEL"].label.lower().startswith("diesel")


def test_word_boundaries_stop_short_aliases_firing_inside_words():
    """'fo' (furnace oil) must not match inside 'foundry' or 'for'."""
    c = extract_from_text("We buy 310 tonnes of silica sand for moulding.")
    assert all(x.key != "FURNACE_OIL" for x in c)


def test_low_confidence_items_require_confirmation():
    for c in extract_from_text(SAMPLE):
        if c.confidence < AUTO_ACCEPT or c.warnings:
            assert c.needs_confirmation


def test_missing_period_is_flagged_never_assumed_silently():
    c = extract_from_text("We consumed 12000 kWh of electricity.")[0]
    assert c.period == "YEAR"
    assert any("assumed" in w for w in c.warnings)
    assert c.needs_confirmation


def test_conflicting_figures_for_one_activity_are_both_kept_and_flagged():
    text = ("Electricity is 480,000 kWh per year. Electricity was 500,000 kWh "
            "per year.")
    cands = [c for c in extract_from_text(text) if c.key == "ELECTRICITY"]
    assert len(cands) == 2
    assert all(c.needs_confirmation for c in cands)
    assert all(any("separate figures" in w for w in c.warnings) for c in cands)


def test_indian_number_words_are_understood():
    c = extract_from_text("We use 4.8 lakh kWh a year.")[0]
    assert c.quantity == pytest.approx(480000)


def test_tabular_extraction_reports_unreadable_units_instead_of_dropping_them():
    rows = [{"Activity": "Grid Electricity", "Quantity": "480000", "Unit": "kWh"},
            {"Activity": "Argon gas", "Quantity": "12", "Unit": "cylinders"}]
    out = extract_from_rows(rows)
    kinds = {c.record_type for c in out}
    assert "UNREADABLE" in kinds
    bad = [c for c in out if c.record_type == "UNREADABLE"][0]
    assert "not supported" in bad.warnings[0]
    assert "guess" in bad.warnings[0]


# --- validation -------------------------------------------------------------
def test_invalid_dates_and_values_never_reach_a_calculation(engine):
    ctx = FactoryContext(factory_id="t", name="T", industry="foundry",
                         country_code="IN", reporting_year=2026)
    bad = [
        ActivityRecord("a", "ENERGY", "Electricity", "ELECTRICITY", -1, "kWh"),
        ActivityRecord("b", "ENERGY", "Electricity", "ELECTRICITY", float("nan"), "kWh"),
        ActivityRecord("c", "ENERGY", "Electricity", "ELECTRICITY", 10, "kWh",
                       period="SHIFT"),
    ]
    fp = engine.calculate(ctx, bad)
    assert fp.calculations == []
    assert len(fp.unresolved) == 3
    assert all(c.kg_co2e is None for c in fp.unresolved)


def test_knowledge_base_rejects_a_record_without_evidence():
    import json
    import tempfile
    from pathlib import Path
    payload = {"interventions": [{
        "slug": "x", "name": "x", "type": "process_improvement", "summary": "x",
        "function": None, "industry": [], "process": [], "current_material": None,
        "alternative": None, "technical_constraints": [], "required_properties": {},
        "circularity_mechanism": "x", "circularity_score": 0.1,
        "impact_model": "NOT_QUANTIFIED", "impact_target_node": None,
        "impact_params": {}, "impact_low": None, "impact_high": None,
        "impact_basis": "x", "capex_model": "NOT_AVAILABLE", "capex_rate_inr": None,
        "capex_low_inr": None, "capex_high_inr": None, "opex_delta_pct": None,
        "cost_basis": "x", "availability": "UNKNOWN", "regions": [],
        "maturity": "UNKNOWN", "typical_lead_time_days": None,
        "prerequisites": [], "conflicts_with": [], "confidence": "low",
        "evidence": []}]}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "kb.json"
        p.write_text(json.dumps(payload))
        try:
            load(p)
            raise AssertionError("should have refused a record with no evidence")
        except KnowledgeBaseError as exc:
            assert "evidence" in str(exc)


def test_every_curated_record_carries_full_provenance(kb):
    for iv in kb:
        assert iv.evidence
        for e in iv.evidence:
            for field in ("claim", "source_name", "source_title", "source_url",
                          "evidence_type", "supports", "confidence"):
                assert getattr(e, field), f"{iv.slug}: evidence missing {field}"


def test_unquantified_records_carry_no_number(kb):
    for iv in kb:
        if iv.impact_model == "NOT_QUANTIFIED":
            assert iv.impact_low is None and iv.impact_high is None
            basis = iv.impact_basis
            assert ("requires facility-specific assessment" in basis
                    or "NOT QUANTIFIED" in basis
                    or "No direct carbon reduction is claimed" in basis), iv.slug


def test_conflicts_reference_real_records(kb):
    slugs = {i.slug for i in kb}
    for iv in kb:
        for c in iv.conflicts_with:
            assert c in slugs
