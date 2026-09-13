import pytest

from app.engines.models import (ASSUMED, ESTIMATED, INVOICED, MEASURED,
                                ActivityRecord, FactoryContext)

IN = FactoryContext(factory_id="t", name="Test", industry="foundry",
                    country_code="IN", reporting_year=2026, annual_production=1000,
                    production_unit="t")


def rec(**kw):
    base = dict(record_id="r1", record_type="ENERGY", label="Grid electricity",
                key="ELECTRICITY", quantity=480000, unit="kWh")
    base.update(kw)
    return ActivityRecord(**base)


def test_core_equation_is_activity_times_factor(engine):
    fp = engine.calculate(IN, [rec()])
    c = fp.calculations[0]
    assert c.kg_co2e == pytest.approx(480000 * 0.678032893, rel=1e-9)
    assert c.factor.source == "CEA"


def test_calculation_is_fully_reproducible_from_its_evidence(engine):
    fp = engine.calculate(IN, [rec()])
    e = fp.calculations[0].evidence()
    recomputed = e["activity"]["normalized"] * e["factor"]["value"]
    assert recomputed == pytest.approx(e["result"]["kg_co2e"], rel=1e-6)
    for k in ("source", "dataset", "version", "geography", "year", "methodology",
              "sheet", "cell", "url", "gas_coverage"):
        assert e["factor"][k] not in (None, "")


def test_period_is_annualised_and_logged(engine):
    fp = engine.calculate(IN, [rec(quantity=40000, period="MONTH")])
    c = fp.calculations[0]
    assert c.annualised_value == pytest.approx(480000)
    assert "12" in c.annualisation_note
    assert c.kg_co2e == pytest.approx(480000 * 0.678032893, rel=1e-9)


def test_unit_conversion_is_logged(engine):
    fp = engine.calculate(IN, [rec(quantity=480, unit="MWh")])
    c = fp.calculations[0]
    assert c.normalized_value == pytest.approx(480000)
    assert "1000" in c.normalization_note or "x 1000" in c.normalization_note


def test_negative_activity_is_rejected(engine):
    fp = engine.calculate(IN, [rec(quantity=-5)])
    assert fp.calculations == []
    assert fp.unresolved[0].status == "INPUT_INVALID"
    assert "negative" in fp.unresolved[0].status_message.lower()


def test_unsupported_unit_is_rejected_with_a_human_message(engine):
    fp = engine.calculate(IN, [rec(unit="bananas")])
    assert fp.unresolved
    msg = fp.unresolved[0].status_message
    assert "unavailable" in msg.lower() or "unsupported" in msg.lower()
    assert "Exception" not in msg and "Error:" not in msg


def test_unknown_activity_says_verified_data_unavailable(engine):
    fp = engine.calculate(IN, [rec(key="UNOBTAINIUM", label="Unobtainium")])
    assert fp.unresolved[0].status == "FACTOR_UNAVAILABLE"
    assert "Verified data unavailable" in fp.unresolved[0].status_message


def test_silica_sand_has_no_verified_factor_and_says_so(engine):
    r = ActivityRecord("m", "MATERIAL", "Silica sand", "SILICA_SAND", 310, "tonnes",
                       material="silica sand", function="moulding")
    fp = engine.calculate(IN, [r])
    assert not fp.calculations
    assert "Verified data unavailable" in fp.unresolved[0].status_message


def test_reference_geography_factor_is_flagged_not_hidden(engine):
    r = ActivityRecord("m", "MATERIAL", "Metal charge", "METAL", 100, "tonnes",
                       material="metals")
    fp = engine.calculate(IN, [r])
    c = fp.calculations[0]
    assert c.applicability == "REFERENCE_ONLY"
    assert any("REFERENCE ONLY" in x for x in c.limitations)


def test_recycled_content_blends_primary_and_closed_loop(engine):
    r = ActivityRecord("m", "MATERIAL", "Metal charge", "METAL", 1000, "tonnes",
                       material="metals", recycled_content_pct=40)
    fp = engine.calculate(IN, [r])
    c = fp.calculations[0]
    assert len(c.components) == 2
    shares = sorted(x["share_pct"] for x in c.components)
    assert shares == [40.0, 60.0]
    expected = 1000 * (0.6 * 3821.95251 + 0.4 * 1636.68611)
    assert c.kg_co2e == pytest.approx(expected, rel=1e-4)


def test_waste_treatment_route_drives_the_factor(engine):
    landfill = ActivityRecord("w", "WASTE", "Spent sand", "SAND", 240, "tonnes",
                              material="soils", treatment="LANDFILL")
    recycled = ActivityRecord("w", "WASTE", "Spent sand", "SAND", 240, "tonnes",
                              material="soils", treatment="RECYCLED")
    a = engine.calculate(IN, [landfill]).calculations[0]
    b = engine.calculate(IN, [recycled]).calculations[0]
    assert "Landfill" in a.factor.variant
    assert "loop" in b.factor.variant.lower()
    assert a.kg_co2e > b.kg_co2e


def test_coverage_is_reported_honestly(engine):
    good = rec()
    bad = rec(record_id="r2", key="UNOBTAINIUM", label="Unobtainium")
    fp = engine.calculate(IN, [good, bad])
    assert fp.coverage_pct == pytest.approx(50.0)
    assert "not a claim of complete Scope" in fp.coverage_detail["statement"]


def test_confidence_reflects_data_quality(engine):
    hi = engine.calculate(IN, [rec(data_quality=MEASURED)]).data_confidence
    lo = engine.calculate(IN, [rec(data_quality=ASSUMED)]).data_confidence
    assert hi > lo


def test_cea_gas_coverage_limitation_surfaces(engine):
    fp = engine.calculate(IN, [rec()])
    assert any("CO2 only" in x for x in fp.calculations[0].limitations)


def test_geography_changes_the_answer(engine):
    us = FactoryContext(factory_id="t", name="T", industry="foundry",
                        country_code="US", reporting_year=2026)
    gb = FactoryContext(factory_id="t", name="T", industry="foundry",
                        country_code="GB", reporting_year=2026)
    a = engine.calculate(IN, [rec()]).total_kg_co2e
    b = engine.calculate(us, [rec()]).total_kg_co2e
    c = engine.calculate(gb, [rec()]).total_kg_co2e
    assert a > b > c
