"""LLM client - explanation only (Master Spec sections 34, 73).

Three guarantees enforced here rather than trusted to the prompt:
  * the model only ever receives the evidence pack the engines built;
  * if no provider is configured the service still answers, from a deterministic
    explainer, so the product never depends on an LLM for correctness;
  * every response is post-checked for numbers that do not appear in the
    evidence, and flagged if any are found.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..core.config import get_settings
from ..engines.evidence import build_messages

log = logging.getLogger("ecoforge.copilot")

NUM = re.compile(r"\d[\d,]*\.?\d*")


class LLMClient:
    def __init__(self):
        self.s = get_settings()

    @property
    def configured(self) -> bool:
        return self.s.llm_configured

    async def explain(self, evidence: Dict[str, Any], question: str
                      ) -> Tuple[str, Dict[str, Any]]:
        if not self.configured:
            return deterministic_answer(evidence, question), {
                "mode": "deterministic",
                "note": ("No LLM provider is configured, so EcoForge answered from "
                         "the engines directly. Every number below is the same "
                         "number the deterministic engine produced."),
            }
        messages = build_messages(evidence, question)
        try:
            text = await self._call(messages)
        except Exception as exc:                             # noqa: BLE001
            log.warning("LLM call failed: %s", exc)
            return deterministic_answer(evidence, question), {
                "mode": "deterministic_fallback",
                "note": "The language model could not be reached, so this answer "
                        "came from the deterministic engine instead.",
                "error": str(exc)[:200],
            }
        unsupported = ungrounded_numbers(text, evidence)
        return text, {
            "mode": "llm",
            "model": self.s.llm_model,
            "grounding_check": {
                "unsupported_numbers": unsupported,
                "passed": not unsupported,
                "note": ("Every number in the answer was checked against the "
                         "evidence pack. Anything listed here did not appear in "
                         "the evidence and must not be relied on."),
            },
        }

    async def _call(self, messages: List[Dict[str, str]]) -> str:
        base = self.s.llm_base_url or "https://api.openai.com/v1"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.s.llm_api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.s.llm_model, "messages": messages,
                      "temperature": 0.2, "max_tokens": 900})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


def ungrounded_numbers(text: str, evidence: Dict[str, Any],
                       tolerance: float = 0.02) -> List[str]:
    """Numbers in the answer that do not appear anywhere in the evidence."""
    blob = json.dumps(evidence, default=str)
    known = {float(m.replace(",", "")) for m in NUM.findall(blob)
             if _is_float(m.replace(",", ""))}
    out = []
    for m in NUM.findall(text):
        raw = m.replace(",", "")
        if not _is_float(raw):
            continue
        v = float(raw)
        if v in (0, 1, 2, 100) or v != v:
            continue
        if any(abs(v - k) <= max(tolerance * abs(k), 0.005) for k in known):
            continue
        out.append(m)
    return sorted(set(out))[:10]


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
def deterministic_answer(evidence: Dict[str, Any], question: str) -> str:
    """A real answer without any model, assembled from the evidence pack.

    This exists so the product degrades into something still useful and still
    correct, rather than into an apology.
    """
    q = question.lower()
    fp = evidence.get("footprint", {})
    leaks = evidence.get("leaks", [])
    recs = evidence.get("recommendations", [])
    port = evidence.get("portfolio")
    scen = evidence.get("scenario")

    def money(x):
        return f"INR {x:,.0f}" if isinstance(x, (int, float)) else "not available"

    if any(w in q for w in ("reject", "why not", "excluded")):
        rejected = [r for r in recs if r.get("status") == "REJECTED"]
        if not rejected:
            return "Nothing was rejected for this factory under the current settings."
        lines = ["These actions were set aside, and here is exactly why:"]
        for r in rejected[:6]:
            blocking = [x["message"] for x in r.get("reasons", []) if x["blocking"]]
            lines.append(f"- {r['name']}: {blocking[0] if blocking else 'no blocking reason recorded'}")
        return "\n".join(lines)

    if any(w in q for w in ("payback", "fastest", "cheapest", "quickest")):
        priced = [r for r in recs if r.get("payback_years")]
        if not priced:
            return ("None of the recommended actions has a payback yet, because a "
                    "capital cost or a price is missing. Enter your tariff and any "
                    "quotations in Settings and EcoForge will calculate it - it will "
                    "not assume a price.")
        priced.sort(key=lambda r: r["payback_years"])
        lines = ["Ranked by payback, using the prices you entered:"]
        for r in priced[:5]:
            lines.append(f"- {r['name']}: {r['payback_years']} years, "
                         f"{money(r.get('capex_inr'))} capital, "
                         f"{r.get('reduction_t_mid')} tCO2e/year.")
        return "\n".join(lines)

    if any(w in q for w in ("budget", "lakh", "spend", "afford")) and port:
        lines = [f"With {money(port['budget_inr'])} the best portfolio EcoForge finds "
                 f"is {port['action_count']} action(s):"]
        for e in port["ledger"]:
            lines.append(f"- {e['name']} ({e['size_label']}): {e['marginal_t']} "
                         f"tCO2e/year, {money(e['capex_inr'])}")
        lines.append(f"Total {port['total_reduction_t']} tCO2e/year "
                     f"({port['reduction_pct']}% of the footprint shown) for "
                     f"{money(port['total_capex_inr'])}, leaving "
                     f"{money(port['unspent_inr'])} unspent.")
        lines.append("Savings are applied one after another against the remaining "
                     "baseline, so overlapping measures are not counted twice.")
        return "\n".join(lines)

    if scen and any(w in q for w in ("what if", "if i select", "scenario", "these")):
        return (f"That scenario takes the footprint from {scen['baseline_t']} to "
                f"{scen['scenario_t']} tCO2e/year, a reduction of "
                f"{scen['reduction_t']} tCO2e ({scen['reduction_pct']}%), for "
                f"{money(scen['capex_inr'])} of capital with a payback of "
                f"{scen.get('payback_years')} years. "
                f"{scen['disclaimer']}")

    if leaks and any(w in q for w in ("biggest", "largest", "leak", "why", "source",
                                      "hotspot")):
        top = leaks[0]
        calc = next((c for c in evidence.get("calculations", [])
                     if c["metric"] == top["label"]), None)
        out = [f"{top['label']} is your biggest carbon leak: {top['t_co2e']} "
               f"tCO2e/year, {top['share_pct']}% of the footprint shown.",
               top["root_cause"]]
        if calc and calc.get("factor"):
            f = calc["factor"]
            out.append(f"The arithmetic: {calc['formula']}")
            out.append(f"The factor comes from {f['dataset']} version "
                       f"{f['version']} ({f['geography']}), cell {f['cell']}. "
                       f"Gas coverage: {f['gas_coverage']}.")
        out.append("Opportunity: " + top["detail"].get("opportunity", ""))
        return "\n\n".join(out)

    lines = [f"Total reported footprint: {fp.get('total_t_co2e')} tCO2e/year across "
             f"the activities entered, at {fp.get('coverage_pct')}% activity coverage "
             f"and {fp.get('data_confidence_pct')}% data confidence."]
    if leaks:
        lines.append("Largest sources: " + ", ".join(
            f"{l['label']} ({l['share_pct']}%)" for l in leaks[:3]) + ".")
    if fp.get("activities_not_resolved"):
        lines.append("Not included, because no verified factor exists for them: "
                     + ", ".join(a["label"] for a in fp["activities_not_resolved"]) + ".")
    lines.append("Ask about a specific leak, your budget, payback, or why something "
                 "was rejected.")
    return " ".join(lines)
