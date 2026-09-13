-- EcoForge AI :: V5 recommendations, optimisation, scenarios, action plan

CREATE TABLE recommendations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id        UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    factory_id         UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    intervention_id    UUID NOT NULL REFERENCES circular_interventions(id),
    hotspot_id         UUID REFERENCES hotspots(id) ON DELETE SET NULL,

    status             VARCHAR(16) NOT NULL,   -- RECOMMENDED | POTENTIAL | REJECTED
    rejection_reasons  JSONB NOT NULL DEFAULT '[]'::jsonb,

    retrieval_score    DOUBLE PRECISION,
    hybrid_score       DOUBLE PRECISION,
    ranking_reasons    JSONB NOT NULL DEFAULT '[]'::jsonb,

    priority_score     DOUBLE PRECISION,
    score_breakdown    JSONB NOT NULL DEFAULT '{}'::jsonb,

    est_reduction_kg_low  DOUBLE PRECISION,
    est_reduction_kg_high DOUBLE PRECISION,
    impact_quantified  BOOLEAN NOT NULL DEFAULT FALSE,
    impact_note        TEXT,

    capex_inr          DOUBLE PRECISION,
    annual_saving_inr  DOUBLE PRECISION,
    payback_years      DOUBLE PRECISION,
    feasibility        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_rec_analysis ON recommendations (analysis_id, status, priority_score DESC);

CREATE TABLE optimization_runs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id         UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    analysis_id        UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    budget_inr         DOUBLE PRECISION NOT NULL,
    max_payback_years  DOUBLE PRECISION,
    min_confidence     VARCHAR(8),
    strictness         VARCHAR(16) NOT NULL DEFAULT 'BALANCED',
    weights            JSONB NOT NULL DEFAULT '{}'::jsonb,
    selected           JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_capex_inr    DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_reduction_kg DOUBLE PRECISION NOT NULL DEFAULT 0,
    reduction_pct      DOUBLE PRECISION NOT NULL DEFAULT 0,
    annual_saving_inr  DOUBLE PRECISION NOT NULL DEFAULT 0,
    blended_payback    DOUBLE PRECISION,
    marginal_ledger    JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE simulation_scenarios (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id         UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    analysis_id        UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    name               TEXT NOT NULL DEFAULT 'Scenario',
    selected_slugs     TEXT[] NOT NULL DEFAULT '{}',
    baseline_kg_co2e   DOUBLE PRECISION NOT NULL,
    scenario_kg_co2e   DOUBLE PRECISION NOT NULL,
    reduction_kg       DOUBLE PRECISION NOT NULL,
    reduction_pct      DOUBLE PRECISION NOT NULL,
    capex_inr          DOUBLE PRECISION NOT NULL DEFAULT 0,
    annual_saving_inr  DOUBLE PRECISION NOT NULL DEFAULT 0,
    payback_years      DOUBLE PRECISION,
    waste_change_kg    DOUBLE PRECISION,
    energy_change_kwh  DOUBLE PRECISION,
    ledger             JSONB NOT NULL DEFAULT '[]'::jsonb,
    assumptions        JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE action_plans (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    analysis_id   UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    summary       TEXT,
    generated_by  VARCHAR(24) NOT NULL DEFAULT 'DETERMINISTIC',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE action_items (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id           UUID NOT NULL REFERENCES action_plans(id) ON DELETE CASCADE,
    sequence          INTEGER NOT NULL,
    horizon           VARCHAR(24) NOT NULL,    -- IMMEDIATE | 30_DAYS | 60_DAYS | 90_DAYS
    title             TEXT NOT NULL,
    description       TEXT,
    owner             TEXT NOT NULL DEFAULT 'Unassigned',
    priority          VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    expected_outcome  TEXT,
    recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
    evidence_ref      JSONB NOT NULL DEFAULT '{}'::jsonb,
    status            VARCHAR(16) NOT NULL DEFAULT 'NOT_STARTED',
    due_date          DATE
);

CREATE TABLE copilot_conversations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    UUID REFERENCES factories(id) ON DELETE CASCADE,
    role          VARCHAR(16) NOT NULL,
    content       TEXT NOT NULL,
    evidence      JSONB NOT NULL DEFAULT '[]'::jsonb,
    model         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_copilot_factory ON copilot_conversations (factory_id, created_at);
