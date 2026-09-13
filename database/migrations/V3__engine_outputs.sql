-- EcoForge AI :: V3 deterministic engine outputs + full calculation provenance
-- (Master Spec sections 15, 45)

CREATE TABLE emission_calculations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id           UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    analysis_id          UUID NOT NULL,
    record_type          VARCHAR(24) NOT NULL,     -- ENERGY | MATERIAL | WASTE | PROCESS
    record_id            UUID NOT NULL,
    label                TEXT NOT NULL,

    activity_value       DOUBLE PRECISION NOT NULL,
    activity_unit        TEXT NOT NULL,
    period               VARCHAR(16) NOT NULL,
    annualised_value     DOUBLE PRECISION NOT NULL,
    annualisation_note   TEXT NOT NULL,
    normalized_value     DOUBLE PRECISION NOT NULL,
    normalized_unit      TEXT NOT NULL,
    normalization_note   TEXT NOT NULL,

    factor_uid           VARCHAR(32) REFERENCES canonical_emission_factors(factor_uid),
    emission_factor      DOUBLE PRECISION,
    factor_unit          TEXT,
    factor_source        VARCHAR(16),
    factor_dataset       TEXT,
    factor_version       TEXT,
    factor_year          INTEGER,
    factor_geography     VARCHAR(8),
    factor_ref           TEXT,
    methodology          TEXT,
    gas_coverage         TEXT,

    result_kg_co2e       DOUBLE PRECISION,
    result_t_co2e        DOUBLE PRECISION,
    formula              TEXT NOT NULL,
    scope                VARCHAR(8),
    category             VARCHAR(48),
    controllability      DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    confidence           DOUBLE PRECISION NOT NULL DEFAULT 0.7,

    status               VARCHAR(24) NOT NULL DEFAULT 'CALCULATED',  -- CALCULATED | FACTOR_UNAVAILABLE | UNIT_UNSUPPORTED
    status_message       TEXT,
    alternatives         JSONB NOT NULL DEFAULT '[]'::jsonb,        -- rejected/reference candidate factors
    calculated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_calc_factory ON emission_calculations (factory_id, analysis_id);
CREATE INDEX ix_calc_status  ON emission_calculations (status);

CREATE TABLE analyses (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id         UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    reporting_year     INTEGER NOT NULL,
    total_kg_co2e      DOUBLE PRECISION NOT NULL DEFAULT 0,
    coverage_pct       DOUBLE PRECISION NOT NULL DEFAULT 0,
    data_confidence    DOUBLE PRECISION NOT NULL DEFAULT 0,
    carbon_health      DOUBLE PRECISION,
    breakdown          JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_detail  JSONB NOT NULL DEFAULT '{}'::jsonb,
    health_detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    unresolved         JSONB NOT NULL DEFAULT '[]'::jsonb,
    status             VARCHAR(24) NOT NULL DEFAULT 'COMPLETE',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_analyses_factory ON analyses (factory_id, created_at DESC);

CREATE TABLE hotspots (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id        UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    factory_id         UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    rank               INTEGER NOT NULL,
    label              TEXT NOT NULL,
    node_key           TEXT NOT NULL,
    category           VARCHAR(48) NOT NULL,
    kg_co2e            DOUBLE PRECISION NOT NULL,
    share_pct          DOUBLE PRECISION NOT NULL,
    controllability    DOUBLE PRECISION NOT NULL,
    confidence         DOUBLE PRECISION NOT NULL,
    severity           VARCHAR(16) NOT NULL,     -- CRITICAL | HIGH | MEDIUM | LOW
    leak_score         DOUBLE PRECISION NOT NULL,
    root_cause         TEXT,
    calculation_ids    UUID[] NOT NULL DEFAULT '{}',
    detail             JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX ix_hotspots_analysis ON hotspots (analysis_id, rank);

CREATE TABLE anomaly_results (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    metric        TEXT NOT NULL,
    status        VARCHAR(32) NOT NULL,      -- OK | ANOMALY | INSUFFICIENT_HISTORY
    value         DOUBLE PRECISION,
    baseline      DOUBLE PRECISION,
    z_score       DOUBLE PRECISION,
    observations  INTEGER NOT NULL DEFAULT 0,
    message       TEXT NOT NULL,
    detail        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE benchmark_results (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    metric        TEXT NOT NULL,
    status        VARCHAR(32) NOT NULL DEFAULT 'UNAVAILABLE',
    value         DOUBLE PRECISION,
    peer_median   DOUBLE PRECISION,
    peer_count    INTEGER,
    dataset       TEXT,
    message       TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id            BIGSERIAL PRIMARY KEY,
    actor         TEXT,
    factory_id    UUID,
    action        VARCHAR(64) NOT NULL,
    entity        VARCHAR(64),
    entity_id     TEXT,
    detail        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_factory ON audit_logs (factory_id, created_at DESC);
