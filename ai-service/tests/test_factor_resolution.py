import pytest

from app.engines.factor_resolver import ResolutionQuery


def test_india_electricity_uses_cea(resolver):
    chosen, cands, notes = resolver.resolve_energy("ELECTRICITY", "kWh", "IN", 2026)
    assert chosen.factor.source == "CEA"
    assert chosen.role == "PRIMARY"
    assert chosen.factor.factor_value == pytest.approx(0.678032893, rel=1e-9)


def test_epa_and_uk_are_not_applicable_to_indian_electricity(resolver):
    chosen, cands, notes = resolver.resolve_energy("ELECTRICITY", "kWh", "IN", 2026)
    assert all(c.factor.source == "CEA" for c in cands)
    joined = " ".join(notes)
    assert "EPA" in joined and "UK2026" in joined


def test_us_electricity_defaults_to_national_average_not_alaska(resolver):
    chosen, _, _ = resolver.resolve_energy("ELECTRICITY", "kWh", "US", 2026)
    assert chosen.factor.source == "EPA"
    assert "US Average" in chosen.factor.region


def test_us_electricity_honours_a_named_subregion(resolver):
    chosen, _, _ = resolver.resolve_energy("ELECTRICITY", "kWh", "US", 2026,
                                           region="CAMX")
    assert "CAMX" in chosen.factor.region


def test_uk_electricity_uses_uk_factor(resolver):
    chosen, _, _ = resolver.resolve_energy("ELECTRICITY", "kWh", "GB", 2026)
    assert chosen.factor.source == "UK2026"
    assert chosen.factor.factor_value == pytest.approx(0.13096)


def test_diesel_never_resolves_to_biodiesel(resolver):
    for geo in ("IN", "US", "GB"):
        chosen, _, _ = resolver.resolve_energy("DIESEL", "litres", geo, 2026)
        label = chosen.factor.label().lower()
        assert "biodiesel" not in label
        assert "biofuel" not in label


def test_indian_diesel_prefers_cea_over_uk_and_epa(resolver):
    chosen, cands, _ = resolver.resolve_energy("DIESEL", "litres", "IN", 2026)
    assert chosen.factor.source == "CEA"
    assert chosen.role == "PRIMARY"
    other = {c.factor.source for c in cands if c.role == "REFERENCE"}
    assert other == {"EPA", "UK2026"}


def test_reconciliation_lists_each_source_once_and_never_averages(resolver):
    _, cands, _ = resolver.resolve_energy("DIESEL", "litres", "IN", 2026)
    rows = resolver.reconcile(cands)
    assert [r["source"] for r in rows] == ["CEA", "EPA", "UK2026"]
    assert rows[0]["role"] == "PRIMARY"
    assert all(r["role"] == "REFERENCE" for r in rows[1:])
    values = [r["value"] for r in rows]
    assert len(set(values)) == 3          # genuinely different, not blended


def test_unit_mismatch_returns_an_explanation_not_a_factor(resolver):
    q = ResolutionQuery(category="electricity", terms=["grid", "electricity"],
                        unit="tonnes", geography="IN", year=2026,
                        prefer_factor_types=["grid_average"], avoid_factor_types=[],
                        prefer_terms=[], avoid_terms=[], variant_terms=[],
                        label="Grid electricity")
    chosen, cands, notes = resolver.resolve(q)
    assert chosen is None
    assert any("supported unit" in n or "expressed per" in n for n in notes)


def test_unsupported_unit_is_refused(resolver):
    q = ResolutionQuery(category="electricity", terms=["electricity"],
                        unit="bananas", geography="IN", year=2026,
                        prefer_factor_types=[], avoid_factor_types=[],
                        prefer_terms=[], avoid_terms=[], variant_terms=[])
    chosen, _, notes = resolver.resolve(q)
    assert chosen is None
    assert any("Unsupported unit" in n for n in notes)


def test_grid_marginal_is_never_used_for_consumption(resolver):
    chosen, cands, _ = resolver.resolve_energy("ELECTRICITY", "kWh", "IN", 2026)
    assert chosen.factor.factor_type == "grid_average"
    assert all(c.factor.factor_type != "grid_marginal" for c in cands)


def test_latest_year_is_preferred(resolver):
    chosen, _, _ = resolver.resolve_energy("ELECTRICITY", "kWh", "IN", 2026)
    assert chosen.factor.year == 2025          # Indian FY 2025-26
