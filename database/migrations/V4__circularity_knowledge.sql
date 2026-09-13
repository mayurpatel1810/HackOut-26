-- EcoForge AI :: V4 curated circularity knowledge base (Level 3) + retrieval
-- This is NOT an emission-factor dataset and is never presented as one
-- (Master Spec sections 2, 22, 23).

CREATE TABLE circular_interventions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                  TEXT NOT NULL UNIQUE,
    name                  TEXT NOT NULL,
    type                  VARCHAR(32) NOT NULL,   -- material_substitution | process_improvement | energy_efficiency | renewable_energy | recycling_loop | waste_recovery | circular_procurement | industrial_symbiosis
    summary               TEXT NOT NULL,

    current_material      TEXT,
    alternative           TEXT,
    function              TEXT,                   -- moulding | abrasive | filler | casting | polishing | heating ...
    industry              TEXT[] NOT NULL DEFAULT '{}',
    process               TEXT[] NOT NULL DEFAULT '{}',

    technical_constraints TEXT[] NOT NULL DEFAULT '{}',
    required_properties   JSONB  NOT NULL DEFAULT '{}'::jsonb,
    circularity_mechanism TEXT NOT NULL,
    circularity_score     DOUBLE PRECISION NOT NULL DEFAULT 0.5,

    -- IMPACT: either a verified mechanism EcoForge can compute against the
    -- factory's own footprint, or nothing. Never an invented tonnage.
    impact_model          VARCHAR(40) NOT NULL,   -- ACTIVITY_DISPLACEMENT | FACTOR_SUBSTITUTION | EFFICIENCY_FRACTION | WASTE_DIVERSION | NOT_QUANTIFIED
    impact_target_node    TEXT,                   -- which footprint node it acts on
    impact_low            DOUBLE PRECISION,       -- fractional reduction of the target node
    impact_high           DOUBLE PRECISION,
    impact_basis          TEXT NOT NULL,

    capex_low_inr         DOUBLE PRECISION,
    capex_high_inr        DOUBLE PRECISION,
    capex_model           VARCHAR(32),            -- FIXED | PER_KW | PER_TONNE | NOT_AVAILABLE
    capex_rate_inr        DOUBLE PRECISION,
    opex_delta_pct        DOUBLE PRECISION,
    cost_basis            TEXT NOT NULL,

    availability          VARCHAR(24) NOT NULL DEFAULT 'UNKNOWN',  -- WIDELY_AVAILABLE | REGIONAL | LIMITED | UNKNOWN
    regions               TEXT[] NOT NULL DEFAULT '{}',
    maturity              VARCHAR(24) NOT NULL DEFAULT 'UNKNOWN',  -- COMMERCIAL | EMERGING | PILOT | RESEARCH
    typical_lead_time_days INTEGER,
    prerequisites         TEXT[] NOT NULL DEFAULT '{}',
    conflicts_with        TEXT[] NOT NULL DEFAULT '{}',            -- slugs that overlap; used for double counting

    confidence            VARCHAR(8) NOT NULL DEFAULT 'medium',
    status                VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ci_type ON circular_interventions (type);
CREATE INDEX ix_ci_fn   ON circular_interventions (lower(function));

CREATE TABLE intervention_evidence (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intervention_id   UUID NOT NULL REFERENCES circular_interventions(id) ON DELETE CASCADE,
    claim             TEXT NOT NULL,
    evidence_type     VARCHAR(32) NOT NULL,   -- STANDARD | GOVERNMENT | PEER_REVIEWED | INDUSTRY_TECHNICAL | DATASET
    source_name       TEXT NOT NULL,
    source_title      TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    publication_year  INTEGER,
    section_ref       TEXT,
    supports          VARCHAR(24) NOT NULL,   -- TECHNICAL | IMPACT | COST | AVAILABILITY | CIRCULARITY
    confidence        VARCHAR(8) NOT NULL DEFAULT 'medium',
    retrieved_at      DATE NOT NULL
);
CREATE INDEX ix_evidence_intervention ON intervention_evidence (intervention_id);

-- Semantic retrieval (Master Spec section 24). Separate logical collections
-- inside one physical table so pgvector stays the only vector store.
CREATE TABLE embeddings (
    id            BIGSERIAL PRIMARY KEY,
    collection    VARCHAR(32) NOT NULL,     -- material_knowledge | process_interventions | circular_loops
    ref_type      VARCHAR(32) NOT NULL,     -- intervention | evidence
    ref_id        UUID NOT NULL,
    chunk_index   INTEGER NOT NULL DEFAULT 0,
    content       TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    model         TEXT NOT NULL,
    embedding     vector(384),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (collection, ref_type, ref_id, chunk_index)
);
CREATE INDEX ix_emb_collection ON embeddings (collection);
CREATE INDEX ix_emb_vector ON embeddings USING hnsw (embedding vector_cosine_ops);
