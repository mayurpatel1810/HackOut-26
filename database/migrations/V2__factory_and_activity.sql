-- EcoForge AI :: V2 tenant, factory profile and operational activity data
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          VARCHAR(24) NOT NULL DEFAULT 'FACTORY_MANAGER',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE factories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id           UUID REFERENCES users(id) ON DELETE SET NULL,
    name               TEXT NOT NULL,
    industry           TEXT NOT NULL,
    production_type    TEXT,
    country_code       VARCHAR(8)  NOT NULL DEFAULT 'IN',
    state_or_region    TEXT,
    city               TEXT,
    grid_region        TEXT,
    is_demo            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE factory_profiles (
    factory_id          UUID PRIMARY KEY REFERENCES factories(id) ON DELETE CASCADE,
    reporting_year      INTEGER NOT NULL,
    reporting_period    VARCHAR(24) NOT NULL DEFAULT 'ANNUAL',
    annual_production   DOUBLE PRECISION,
    production_unit     TEXT,
    employees           INTEGER,
    floor_area_m2       DOUBLE PRECISION,
    annual_budget_inr   DOUBLE PRECISION,
    currency            VARCHAR(8) NOT NULL DEFAULT 'INR',
    target_reduction_pct DOUBLE PRECISION,
    -- Prices the FACTORY supplies. EcoForge never assumes a tariff: without a
    -- price it reports "verified data unavailable" instead of a saving.
    electricity_tariff_inr_per_kwh   DOUBLE PRECISION CHECK (electricity_tariff_inr_per_kwh >= 0),
    diesel_price_inr_per_litre       DOUBLE PRECISION CHECK (diesel_price_inr_per_litre >= 0),
    gas_price_inr_per_m3             DOUBLE PRECISION CHECK (gas_price_inr_per_m3 >= 0),
    lpg_price_inr_per_kg             DOUBLE PRECISION CHECK (lpg_price_inr_per_kg >= 0),
    waste_disposal_cost_inr_per_tonne DOUBLE PRECISION CHECK (waste_disposal_cost_inr_per_tonne >= 0),
    notes               TEXT
);

-- Shared columns on every activity table:
--   quantity / unit          : exactly as the user entered them
--   period                   : DAY | MONTH | YEAR ... annualised explicitly
--   data_quality             : MEASURED | INVOICED | ESTIMATED | ASSUMED
--   confidence               : 0..1, drives FACTORY DATA CONFIDENCE
--   provenance               : MANUAL | COPILOT_TEXT | FILE_UPLOAD | DEMO_SEED
CREATE TABLE energy_records (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    energy_type   TEXT NOT NULL,              -- ELECTRICITY | DIESEL | NATURAL_GAS | LPG | COAL | ...
    quantity      DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    unit          TEXT NOT NULL,
    period        VARCHAR(16) NOT NULL DEFAULT 'YEAR',
    period_start  DATE,
    period_end    DATE,
    source_label  TEXT,
    data_quality  VARCHAR(16) NOT NULL DEFAULT 'ESTIMATED',
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0.7 CHECK (confidence BETWEEN 0 AND 1),
    provenance    VARCHAR(24) NOT NULL DEFAULT 'MANUAL',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE material_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id       UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    material         TEXT NOT NULL,
    material_grade   TEXT,
    function         TEXT,                    -- moulding | polishing | abrasive | filler | casting
    quantity         DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    unit             TEXT NOT NULL,
    period           VARCHAR(16) NOT NULL DEFAULT 'YEAR',
    recycled_content_pct DOUBLE PRECISION CHECK (recycled_content_pct BETWEEN 0 AND 100),
    supplier         TEXT,
    supplier_region  TEXT,
    unit_cost        DOUBLE PRECISION,
    data_quality     VARCHAR(16) NOT NULL DEFAULT 'ESTIMATED',
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 0.6 CHECK (confidence BETWEEN 0 AND 1),
    provenance       VARCHAR(24) NOT NULL DEFAULT 'MANUAL',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE process_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id       UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    process_name     TEXT NOT NULL,
    process_type     TEXT,
    machine_type     TEXT,
    operating_hours  DOUBLE PRECISION,
    energy_share_pct DOUBLE PRECISION CHECK (energy_share_pct BETWEEN 0 AND 100),
    material_input   TEXT,
    output_quantity  DOUBLE PRECISION,
    output_unit      TEXT,
    scrap_rate_pct   DOUBLE PRECISION CHECK (scrap_rate_pct BETWEEN 0 AND 100),
    operating_temp_c DOUBLE PRECISION,
    data_quality     VARCHAR(16) NOT NULL DEFAULT 'ESTIMATED',
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 0.6 CHECK (confidence BETWEEN 0 AND 1),
    provenance       VARCHAR(24) NOT NULL DEFAULT 'MANUAL',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE waste_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id       UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    waste_type       TEXT NOT NULL,
    quantity         DOUBLE PRECISION NOT NULL CHECK (quantity >= 0),
    unit             TEXT NOT NULL,
    period           VARCHAR(16) NOT NULL DEFAULT 'YEAR',
    treatment        TEXT NOT NULL,           -- LANDFILL | RECYCLED | COMBUSTED | REUSED | COMPOSTED
    recovered_pct    DOUBLE PRECISION CHECK (recovered_pct BETWEEN 0 AND 100),
    disposal_cost    DOUBLE PRECISION,
    data_quality     VARCHAR(16) NOT NULL DEFAULT 'ESTIMATED',
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 0.7 CHECK (confidence BETWEEN 0 AND 1),
    provenance       VARCHAR(24) NOT NULL DEFAULT 'MANUAL',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
