-- EcoForge AI :: V1 extensions + verified reference data (Level 1 of the
-- system-of-record hierarchy, Master Spec section 5)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------------
-- Dataset-level provenance
-- ---------------------------------------------------------------------------
CREATE TABLE factor_sources (
    source_code      VARCHAR(16)  PRIMARY KEY,          -- CEA | EPA | UK2026
    dataset_name     TEXT         NOT NULL,
    dataset_version  TEXT         NOT NULL,
    publisher        TEXT         NOT NULL,
    geography        VARCHAR(8)   NOT NULL,
    source_url       TEXT         NOT NULL,
    raw_file         TEXT         NOT NULL,
    factor_count     INTEGER      NOT NULL DEFAULT 0,
    ingested_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Canonical emission factors (Master Spec sections 44 + 50)
-- Every downstream component reads THIS table, never a spreadsheet.
-- ---------------------------------------------------------------------------
CREATE TABLE canonical_emission_factors (
    id                BIGSERIAL PRIMARY KEY,
    factor_uid        VARCHAR(32) NOT NULL UNIQUE,
    source            VARCHAR(16) NOT NULL REFERENCES factor_sources(source_code),

    category          VARCHAR(48) NOT NULL,
    activity          TEXT        NOT NULL,
    subcategory       TEXT,
    fuel              TEXT,
    material          TEXT,
    variant           TEXT,
    scope             VARCHAR(8),

    factor_value      DOUBLE PRECISION NOT NULL,
    factor_unit       TEXT             NOT NULL,
    activity_unit     TEXT             NOT NULL,
    canonical_unit    VARCHAR(24),
    quantity_kind     VARCHAR(24),
    unit_supported    BOOLEAN          NOT NULL DEFAULT TRUE,

    co2_factor        DOUBLE PRECISION,
    ch4_factor        DOUBLE PRECISION,
    n2o_factor        DOUBLE PRECISION,
    gas_coverage      TEXT        NOT NULL,

    factor_type       VARCHAR(32) NOT NULL,
    geography         VARCHAR(8)  NOT NULL,
    region            TEXT,
    year              INTEGER,
    valid_from        DATE,

    dataset_name      TEXT NOT NULL,
    dataset_version   TEXT NOT NULL,
    publisher         TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    source_sheet      TEXT NOT NULL,
    source_ref        TEXT NOT NULL,
    methodology       TEXT NOT NULL,
    derivation        TEXT,
    notes             TEXT,
    quality           VARCHAR(8)  NOT NULL DEFAULT 'high',
    quality_score     DOUBLE PRECISION GENERATED ALWAYS AS
                      (CASE quality WHEN 'high' THEN 0.95 WHEN 'medium' THEN 0.75
                                    ELSE 0.50 END) STORED,

    search_text       TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ef_value_finite CHECK (factor_value >= 0),
    CONSTRAINT ef_scope_valid  CHECK (scope IS NULL OR scope IN ('1','2','3','outside'))
);

CREATE INDEX ix_ef_lookup     ON canonical_emission_factors (category, geography, canonical_unit, year DESC);
CREATE INDEX ix_ef_activity   ON canonical_emission_factors (lower(activity));
CREATE INDEX ix_ef_fuel       ON canonical_emission_factors (lower(fuel));
CREATE INDEX ix_ef_material   ON canonical_emission_factors (lower(material));
CREATE INDEX ix_ef_type       ON canonical_emission_factors (factor_type);
CREATE INDEX ix_ef_search_trgm ON canonical_emission_factors USING gin (to_tsvector('english', search_text));

-- Reference tables kept OUT of the factor table on purpose: they are physical
-- properties, not emission factors, and must never be resolvable as one.
CREATE TABLE unit_conversions (
    id          BIGSERIAL PRIMARY KEY,
    family      VARCHAR(24) NOT NULL,
    from_unit   TEXT NOT NULL,
    to_unit     TEXT NOT NULL,
    multiplier  DOUBLE PRECISION NOT NULL,
    source_ref  TEXT NOT NULL,
    source      VARCHAR(16) NOT NULL DEFAULT 'UK2026'
);

CREATE TABLE fuel_properties (
    id          BIGSERIAL PRIMARY KEY,
    fuel        TEXT NOT NULL,
    fuel_group  TEXT,
    property    TEXT NOT NULL,
    unit        TEXT,
    value       DOUBLE PRECISION NOT NULL,
    year        INTEGER,
    source_ref  TEXT NOT NULL,
    source      VARCHAR(16) NOT NULL DEFAULT 'UK2026'
);

-- Geography applicability policy (Master Spec sections 16, 17, 51).
-- Data, not code, so the rules are auditable and editable without a rebuild.
CREATE TABLE factor_source_policy (
    id                 BIGSERIAL PRIMARY KEY,
    category           VARCHAR(48) NOT NULL,
    factory_geography  VARCHAR(8)  NOT NULL,
    source             VARCHAR(16) NOT NULL REFERENCES factor_sources(source_code),
    role               VARCHAR(16) NOT NULL,   -- PRIMARY | REFERENCE | NOT_APPLICABLE
    rank               INTEGER     NOT NULL,
    rationale          TEXT        NOT NULL,
    UNIQUE (category, factory_geography, source)
);
