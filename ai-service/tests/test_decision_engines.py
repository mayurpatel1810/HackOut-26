"""Leak ranking, retrieval, feasibility, optimisation, double counting."""
import pytest

from app.engines.feasibility import Constraints
from app.engines.leak_finder import VIEW_FULL, VIEW_OPERATIONAL, find_leaks
from app.engines.retrieval import RetrievalContext


@pytest.fixture(scope="session")
def analysis(service, demo):
    ctx, records, history, procs = demo
    return service.analyse(ctx, records, view=VIEW_OPERATIONAL,
                           constraints=Constraints(budget_inr=1_500_000,
                                                   max_payback_years=7),
                           history=history, process_records=procs)


# --- leaks ------------------------------------------------------------------
def test_biggest_leak_is_electricity_for_this_factory(analysis):
    top = analysis.hotspots[0]
    assert top.node_key == "energy.electricity"
    assert top.severity == "CRITICAL"
    assert top.share_pct > 50


def test_leak_score_is_gated_by_contribution(analysis):
    shares = [h.share_pct for h in analysis.hotspots]
    assert shares == sorted(shares, reverse=True)


def test_every_leak_explains_itself(analysis):
    for h in analysis.hotspots:
        assert len(h.root_cause) > 60
        assert h.detail["opportunity"]
        assert h.calculation_ids


def test_operational_and_full_views_differ(service, demo):
    ctx, records, history, procs = demo
    op = service.analyse(ctx, records, view=VIEW_OPERATIONAL)
    full = service.analyse(ctx, records, view=VIEW_FULL)
    assert op.hotspots[0].node_key == "energy.electricity"
    assert full.hotspots[0].node_key.startswith("material.")


# --- carbon health ----------------------------------------------------------
def test_carbon_health_is_labelled_as_not_a_certification(analysis):
    assert 0 <= analysis.health <= 100
    assert "not an official certification" in analysis.health_detail["disclaimer"]


# --- retrieval --------------------------------------------------------------
def test_retrieval_is_function_aware_not_name_aware(service):
    moulding = RetrievalContext(
        industry="foundry", country_code="IN", processes=["green sand moulding"],
        materials=["silica sand"], functions=["moulding"],
        hot_nodes=["waste.sand_waste"])
    abrasive = RetrievalContext(
        industry="foundry", country_code="IN", processes=["shot blasting"],
        materials=["steel shot"], functions=["abrasive"],
        hot_nodes=["energy.electricity"])
    a = [r.intervention.slug for r in service.retriever.retrieve(moulding, k=3)]
    b = [r.intervention.slug for r in service.retriever.retrieve(abrasive, k=3)]
    assert "mechanical-sand-reclamation" in a
    assert "reclaimed-abrasive-shot-blasting" in b
    assert a[0] != b[0]


def test_ranking_records_its_reasons(service, analysis):
    for r in analysis.retrieved[:5]:
        assert r.reasons
        assert any("components" in x for x in r.reasons)


def test_hybrid_score_is_not_pure_cosine(analysis):
    by_semantic = sorted(analysis.retrieved, key=lambda r: -r.semantic)
    by_hybrid = sorted(analysis.retrieved, key=lambda r: -r.hybrid)
    assert [r.intervention.slug for r in by_semantic[:5]] != \
           [r.intervention.slug for r in by_hybrid[:5]]


# --- feasibility ------------------------------------------------------------
def test_every_rejection_has_a_reason(analysis):
    for a in analysis.assessments:
        if a.status == "REJECTED":
            assert any(r["blocking"] for r in a.reasons)
            assert all(r["message"] for r in a.reasons)


def test_over_budget_actions_are_rejected_by_name(analysis):
    codes = {r["code"] for a in analysis.assessments for r in a.reasons}
    assert "CAPEX_EXCEEDS_BUDGET" in codes


def test_an_action_that_increases_emissions_is_rejected(analysis):
    elec = [a for a in analysis.assessments
            if a.estimate.option.slug == "electrify-heat-treatment"]
    assert elec and elec[0].status == "REJECTED"
    assert any(r["code"] == "INCREASES_EMISSIONS" for r in elec[0].reasons)
    assert elec[0].estimate.increases_emissions


def test_unquantified_impact_is_potential_never_recommended(analysis):
    for a in analysis.assessments:
        if not a.estimate.quantified:
            assert a.status in ("POTENTIAL", "REJECTED")
            assert a.estimate.mid_kg is None


def test_market_based_instrument_does_not_move_a_location_based_footprint(analysis):
    green = [a for a in analysis.assessments
             if a.estimate.option.slug == "green-power-open-access"][0]
    assert not green.estimate.quantified
    assert "market-based" in green.estimate.option.intervention.impact_basis.lower()


def test_priority_score_breakdown_is_exposed(analysis):
    scored = [a for a in analysis.assessments if a.priority_score is not None]
    assert scored
    for a in scored[:3]:
        for k in ("co2_reduction", "cost_efficiency", "payback",
                  "technical_feasibility", "circularity_value", "confidence"):
            assert k in a.score_breakdown


# --- optimisation and double counting ---------------------------------------
def test_portfolio_respects_the_budget(service, analysis):
    for budget in (300_000, 1_000_000, 2_500_000):
        p = service.optimise(analysis, budget)
        assert p.total_capex_inr <= budget


def test_more_budget_never_reduces_impact(service, analysis):
    curve = service.budget_curve(analysis, [300_000, 600_000, 1_000_000,
                                            1_500_000, 2_500_000, 5_000_000])
    reductions = [c["reduction_t"] for c in curve]
    assert reductions == sorted(reductions)


def test_optimiser_total_is_the_sum_of_marginals_not_standalones(service, analysis):
    p = service.optimise(analysis, 2_500_000)
    assert p.ledger
    assert sum(e.marginal_kg for e in p.ledger) == pytest.approx(
        p.total_reduction_kg, rel=1e-6)
    assert sum(e.standalone_kg for e in p.ledger) >= p.total_reduction_kg


def test_overlapping_measures_have_savings_withheld(service, analysis):
    """Three measures that all act on the electricity node must not add up to
    the sum of their standalone savings."""
    slugs = ["led-lighting-retrofit", "vfd-motor-drives",
             "compressed-air-leak-management"]
    sim = service.simulate(analysis, slugs)
    assert len(sim["ledger"]) == 3
    standalone = sum(e["standalone_t"] for e in sim["ledger"])
    assert sim["reduction_t"] < standalone
    assert any(e["overlap_t"] > 0 for e in sim["ledger"])
    assert "never claim the same tonne twice" in sim["double_counting_note"]


def test_portfolio_total_never_exceeds_the_footprint(service, analysis):
    p = service.optimise(analysis, 50_000_000)
    assert p.total_reduction_kg <= p.baseline_kg
    assert p.reduction_pct <= 100.0


def test_unpriced_and_unquantified_actions_are_reported_not_silently_dropped(
        service, analysis):
    p = service.optimise(analysis, 1_500_000)
    joined = " ".join(p.notes)
    assert "no verified cost" in joined or "not quantifiable" in joined


# --- simulation -------------------------------------------------------------
def test_simulator_marks_values_as_scenario(service, analysis):
    sim = service.simulate(analysis, ["rooftop-solar-pv",
                                      "compressed-air-leak-management"])
    assert sim["label"] == "Scenario simulation"
    assert "not guaranteed" in sim["disclaimer"]


def test_simulator_skips_mutually_exclusive_routes(service, analysis):
    sim = service.simulate(analysis, ["mechanical-sand-reclamation",
                                      "thermal-sand-reclamation"])
    assert len(sim["skipped"]) == 1
    assert "exclusive" in sim["skipped"][0]["reason"]


def test_simulator_and_optimiser_agree_on_the_same_set(service, analysis):
    p = service.optimise(analysis, 2_500_000)
    variants = [a.estimate.option.variant_id for a in p.selected]
    sim = service.simulate(analysis, variants)
    assert sim["reduction_t"] == pytest.approx(p.total_reduction_kg / 1000, rel=0.02)


# --- anomaly and benchmark --------------------------------------------------
def test_anomaly_engine_flags_the_seeded_spike(analysis):
    elec = [a for a in analysis.anomalies if a.metric == "electricity_kwh"][0]
    assert elec.status == "ANOMALY"
    assert "higher" in elec.message


def test_anomaly_engine_refuses_to_invent_a_baseline(analysis):
    thin = [a for a in analysis.anomalies if a.status == "INSUFFICIENT_HISTORY"]
    assert thin
    assert "will not invent" in thin[0].message


def test_benchmark_is_unavailable_rather_than_fabricated(analysis):
    assert analysis.benchmark[0]["status"] == "UNAVAILABLE"
    assert "will not invent peer companies" in analysis.benchmark[0]["message"]


# --- twin -------------------------------------------------------------------
def test_twin_nodes_link_back_to_calculations(analysis):
    leaves = [n for n in analysis.twin["nodes"]
              if n["kind"] == "leaf" and n["group"] == "energy"]
    assert leaves
    for n in leaves:
        assert n["calculation_ids"]
        assert n["factor"]["ref"]


def test_twin_process_nodes_are_attribution_only(analysis):
    procs = [n for n in analysis.twin["nodes"] if n["group"] == "process"
             and n["kind"] == "leaf"]
    assert procs
    assert all(n["attribution_only"] for n in procs)
