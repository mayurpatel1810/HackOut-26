# DEMO_GUIDE.md — the 4-minute judging walkthrough

**Before you start:** `docker compose up --build`, sign up, and confirm
**Shakti Precision Castings** is selected in the header. Keep the scope toggle on
**Scope 1+2**.

The demo factory stores *only operational inputs*. Every figure below is
calculated live from CEA/EPA/UK factors. Say that out loud — it is the point.

---

### 0:00 · Landing → Control Room (20 s)
"Turn factory emissions into your next business decision."
Click **Explore demo factory**. The loading screen lists the real pipeline —
resolving factors, detecting leaks, checking feasibility — because that is what
is actually happening.

### 0:20 · The headline (30 s)
> **587.8 tCO₂e/year · 87.5 % coverage · 49.3 % data confidence · Carbon Health 68**

Lead with coverage, not the total: *"87.5 %, not 100 %, and here is the 12.5 %
we could not calculate."* The alert at the top says silica sand has no verified
factor in any of the three datasets.

### 0:50 · The leak (40 s)
> **#1 Grid electricity — 325.5 t, 55.4 % — CRITICAL**

Open **Carbon Leaks**. Read the root cause aloud: 480,000 kWh a year meeting a
CEA grid factor of 0.678 kgCO₂/kWh.

Click **Evidence** on any number. The Passport shows the activity, the
annualisation, the unit conversion, the factor, CEA version 22.0, and the cell
**`Results!O14`**. Scroll to *Factors considered and not used* — EPA and UK are
listed as NOT APPLICABLE with the reason, never averaged in.

> **The line to say:** *"The UK 2026 Overseas electricity sheet publishes no
> factors at all this year. So for Indian grid electricity, CEA is not just
> preferred — it is the only verified option, and we show you that."*

### 1:30 · Function-aware retrieval (30 s)
Open **Circular Solutions**. Top results are sand reclamation and foundry
interventions — because the demo factory recorded silica sand with
`function = moulding`.

> *"If the same sand were recorded as an abrasive, the top result would be
> closed-loop abrasive recovery instead. We search by what the material does,
> not by its name."*

### 2:00 · The rejections (30 s)
Switch to the **Rejected** tab.

> **Electrify gas-fired heat treatment — "On your current emission factors this
> action would INCREASE reported emissions."**

Open it: 982,502 kWh of gas → 540,376 kWh of useful heat → 635,737 kWh of
electricity → **431.1 t against 174.7 t today. An increase of 256 t.**

> *"Most tools would recommend electrification because it sounds green. On the
> 2025-26 Indian grid it makes things worse, and we say so. The same action
> becomes attractive once the grid cleans up — which is what the What-If Lab is
> for."*

Also show **Renewable power through open access**, marked *not quantified*:
under GHG Protocol Scope 2 guidance a green tariff moves the market-based
figure, not the location-based one we calculate. Claiming it would be double
counting.

### 2:30 · Budget-to-Impact Studio (45 s)
Open **Decision Studio** and drag the budget slider.

| Budget | Actions | Reduction |
|---|---|---|
| ₹3 L | 1 | 13.1 t |
| ₹6 L | 2 | 24.5 t |
| ₹10 L | 3 | 33.0 t |
| ₹25 L | 4 | 59.6 t |

The portfolio recomposes at each step. Scroll to the **marginal ledger** and
point at the overlap column:

> *"Compressed air standalone saves 8.54 t. After rooftop solar it saves 5.99 t.
> The 2.55 t difference is overlap, and we withhold it. Add the standalone
> numbers and you overstate the plan — that is the most common lie in this
> category, and it is structurally impossible here."*

### 3:15 · What-If Lab (25 s)
Toggle solar + compressed air + burner tuning. Watch the before/after bars move.
Then toggle **both** sand reclamation routes — one is skipped as *mutually
exclusive*, because they are alternative routes for the same stream.

### 3:40 · Carbon Twin + Copilot (20 s)
Open **Carbon Twin**: leaves → groups → factory, sized by share, with process
nodes on a dashed link because they are an *attribution* of energy, not an extra
source. Click any node for its evidence.

Finish in **AI Copilot**: *"What can I do with 15 lakh?"* Point at the badge
under the answer — **"Every number traced to the evidence"** — and note it works
with no LLM configured at all.

---

## The three sentences to close on

1. **"Every number opens to the workbook cell it came from."**
2. **"We reject the action that sounds green but would increase emissions on
   India's grid, and we show the arithmetic."**
3. **"Overlapping savings are structurally impossible to double count here."**

## If something breaks

| Symptom | Say this, then |
|---|---|
| Analysis spins | "The engine is resolving 3,891 factors" — it is a cold start; it warms in one request |
| A chart is empty | Check the scope toggle; Scope 3 material dwarfs operational and changes the ranking |
| Copilot slow | It is assembling a ~180 KB evidence pack; the deterministic mode is instant |
