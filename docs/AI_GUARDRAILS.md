# AI_GUARDRAILS.md

## The rule

The language model may **explain**. It may never **produce a number**.

This is enforced in four places, not asserted in a prompt.

## 1. The model cannot reach the data

The LLM has no database connection, no access to the factor table and no tool
calls. It receives exactly one thing: a JSON evidence pack assembled by
`app/engines/evidence.py` from engine output that has already been computed.
There is no code path by which it can look anything up.

## 2. The system policy

`SYSTEM_POLICY` in `app/engines/evidence.py`, verbatim in the product:

> Use ONLY the evidence supplied. Never invent or estimate an emission factor, a
> cost, a payback, a technical property, a supplier, an availability claim, a
> benchmark or a carbon saving. Never recompute or adjust a number — the numbers
> were produced by a deterministic engine from verified datasets; quote them as
> they are. If the evidence does not contain what is needed, say plainly that
> the data is not available and state what additional evidence would be
> required. Never claim a result is guaranteed. When you state a number, say
> where it came from. Explain in plain language.

The pack itself carries a `hard_limits` array restating the boundaries in the
same payload the model reads.

## 3. Post-hoc grounding check

`ungrounded_numbers()` extracts every numeric token from the model's answer and
matches it against every number in the evidence pack within a 2 % tolerance.
Anything unmatched is returned in the response as
`meta.grounding_check.unsupported_numbers`, and the UI renders a red
**"Grounding check failed"** notice naming the offending figures.

This catches the failure the prompt cannot: a plausible-looking factor the model
produced from its own weights.

## 4. It works with no model at all

`deterministic_answer()` answers the product's core questions — biggest leak,
what a budget buys, fastest payback, why something was rejected, what a scenario
does — directly from the evidence pack, with no model in the loop. The response
is labelled `mode: "deterministic"`.

So EcoForge never *depends* on an LLM for correctness. Configure one and the
prose improves; the numbers do not change.

## What the model may do

explain · summarise · compare items already in the evidence · prioritise them ·
translate a technical result into plain language · draft an action plan from
what the engines produced.

## What it may not do

invent a number of any kind · recompute or adjust a result · assert technical
compatibility, availability or a saving the evidence does not state · claim a
guaranteed outcome · override anything the engines decided.

## Where the *other* AI sits

| Component | Role | Can it change a number? |
|---|---|---|
| NL extraction | Regex + unit vocabulary reads quantities out of the user's own text | No — and nothing is committed without confirmation |
| Embeddings | sentence-transformers (or TF-IDF fallback) | No — retrieval order only |
| Hybrid rerank | Deterministic weighted scoring | No — ordering only, with reasons recorded |
| Anomaly detection | Median/MAD + IsolationForest | No — flags, never edits |
| Optimiser | Beam search over sequences | It *selects*; every value comes from the emission engine |
| LLM | Explanation | **No** |

The extraction layer deserves a note: even when an LLM is configured, it never
supplies the number. The regex layer reads the figure out of the user's text, so
a hallucinated consumption figure is structurally impossible.

## Standing honesty behaviours

* Missing factor → *"Verified data unavailable"* plus what evidence would be needed.
* Wrong-geography factor → used, labelled `REFERENCE ONLY`, confidence reduced.
* Unquantifiable intervention → *"Carbon impact requires facility-specific
  assessment"*, and it is never counted in a portfolio total.
* No peer dataset → *"Benchmark unavailable"*, never a fabricated comparison.
* Thin history → *"Insufficient historical data for anomaly detection"*, never an
  invented baseline.
* An action that would increase emissions → reported as an increase and rejected.
* Scenario values → always labelled *"Scenario simulation"* and *"not guaranteed"*.
