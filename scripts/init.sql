

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- ============================
-- TRIGGER FUNCTION  
-- ============================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- ============================================================================
-- OWNERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS owners (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       VARCHAR(255) NOT NULL,
    role       VARCHAR(50)  NOT NULL CHECK (role IN ('data_steward', 'admin', 'technical_owner', 'business_owner')),
    email      VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_owners_role  ON owners(role);
CREATE INDEX IF NOT EXISTS idx_owners_email ON owners(email);   -- added: useful for lookup-by-email


-- default admin user (idempotent)
-- default admin user (idempotent, no constraint required)
INSERT INTO owners (id, name, role, email)
SELECT 
    uuid_generate_v4(),
    'MG admin',
    'admin',
    'mgadmin1234@gmail.com'
WHERE NOT EXISTS (
    SELECT 1 FROM owners WHERE email = 'mgadmin1234@gmail.com'
);

DROP TRIGGER IF EXISTS update_owners_updated_at ON owners;
CREATE TRIGGER update_owners_updated_at
    BEFORE UPDATE ON owners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATA SOURCES
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_sources (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name               VARCHAR(255) NOT NULL,
    source_type        VARCHAR(50)  NOT NULL,
    connection_details JSONB        NOT NULL,
    description        TEXT,
    include_views      BOOLEAN DEFAULT TRUE,
    include_tables     BOOLEAN DEFAULT TRUE,
    schema_pattern     JSONB,
    table_pattern      JSONB,
    status             VARCHAR(50)  DEFAULT 'running' CHECK (status IN ('running', 'failed', 'success')),
    schedule           VARCHAR(50)  DEFAULT '00:00 GMT+5:30',
    owner_id           UUID REFERENCES owners(id) ON DELETE SET NULL,
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_ingested_at   TIMESTAMP WITH TIME ZONE,
    UNIQUE(name)
);

-- Idempotent migrations
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='data_sources' AND column_name='schedule') THEN
        ALTER TABLE data_sources ADD COLUMN schedule VARCHAR(50) DEFAULT '00:00 GMT+5:30';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='data_sources' AND column_name='owner_id') THEN
        ALTER TABLE data_sources ADD COLUMN owner_id UUID REFERENCES owners(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_data_sources_type     ON data_sources(source_type);   -- added: filter by type
CREATE INDEX IF NOT EXISTS idx_data_sources_status   ON data_sources(status);        -- added: filter by status
CREATE INDEX IF NOT EXISTS idx_data_sources_owner    ON data_sources(owner_id);      -- added: filter by owner

DROP TRIGGER IF EXISTS update_data_sources_updated_at ON data_sources;
CREATE TRIGGER update_data_sources_updated_at
    BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INGESTION JOBS
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id         UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    status            VARCHAR(50) DEFAULT 'running' CHECK (status IN ('running', 'failed', 'success')),
    completed_at      TIMESTAMP WITH TIME ZONE,
    records_ingested  INTEGER DEFAULT 0,
    error_message     TEXT,
    config            JSONB,
    metadata          JSONB,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_source      ON ingestion_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status      ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_created_at  ON ingestion_jobs(created_at DESC);  -- added: latest jobs first

-- ============================================================================
-- CATALOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS catalogs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id     UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    database_name VARCHAR(255),
    schema_name   VARCHAR(255),
    table_name    VARCHAR(255) NOT NULL,
    full_name     VARCHAR(512) GENERATED ALWAYS AS (
        CASE
            WHEN database_name IS NOT NULL AND schema_name IS NOT NULL
                THEN database_name || '.' || schema_name || '.' || table_name
            WHEN schema_name IS NOT NULL
                THEN schema_name || '.' || table_name
            ELSE table_name
        END
    ) STORED,
    description   TEXT,
    row_count     BIGINT,
    owner_id      UUID REFERENCES owners(id) ON DELETE SET NULL,
    metadata      JSONB,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    type          VARCHAR(10)  DEFAULT 'table' CHECK (type IN ('table', 'view')),
    status        VARCHAR(20)  DEFAULT 'healthy' CHECK (status IN ('healthy', 'warning', 'risk')),
    UNIQUE(source_id, database_name, schema_name, table_name)
);

-- Idempotent migrations
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='catalogs' AND column_name='row_count') THEN
        ALTER TABLE catalogs ADD COLUMN row_count BIGINT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='catalogs' AND column_name='owner_id') THEN
        ALTER TABLE catalogs ADD COLUMN owner_id UUID REFERENCES owners(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='catalogs' AND column_name='type') THEN
        ALTER TABLE catalogs ADD COLUMN type VARCHAR(10) DEFAULT 'table' CHECK (type IN ('table', 'view'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='catalogs' AND column_name='status') THEN
        ALTER TABLE catalogs ADD COLUMN status VARCHAR(20) DEFAULT 'healthy' CHECK (status IN ('healthy', 'warning', 'risk'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_catalogs_source     ON catalogs(source_id);
CREATE INDEX IF NOT EXISTS idx_catalogs_full_name  ON catalogs(full_name);
CREATE INDEX IF NOT EXISTS idx_catalogs_owner      ON catalogs(owner_id);              -- added: filter by owner
CREATE INDEX IF NOT EXISTS idx_catalogs_schema     ON catalogs(schema_name);           -- added: filter by schema
CREATE INDEX IF NOT EXISTS idx_catalogs_search     ON catalogs USING GIN (
    to_tsvector('english', COALESCE(table_name, '') || ' ' || COALESCE(description, ''))
);

DROP TRIGGER IF EXISTS update_catalogs_updated_at ON catalogs;
CREATE TRIGGER update_catalogs_updated_at
    BEFORE UPDATE ON catalogs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- CATALOGS - Auto-set owner_id from data_sources on insert / if null
-- ============================================================================

CREATE OR REPLACE FUNCTION set_catalog_owner_from_source()
RETURNS TRIGGER AS $$
BEGIN
    -- Only set if the incoming owner_id is NULL
    -- (preserves manual overrides)
    IF NEW.owner_id IS NULL THEN
        NEW.owner_id := (
            SELECT owner_id 
            FROM data_sources 
            WHERE id = NEW.source_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_catalogs_set_owner ON catalogs;

CREATE TRIGGER trg_catalogs_set_owner
    BEFORE INSERT OR UPDATE OF owner_id
    ON catalogs
    FOR EACH ROW
    EXECUTE FUNCTION set_catalog_owner_from_source();

-- ============================================================================
-- COLUMNS
-- ============================================================================

CREATE TABLE IF NOT EXISTS columns (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id       UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    name             VARCHAR(255) NOT NULL,
    ordinal_position INTEGER,
    data_type        VARCHAR(100),
    is_nullable      BOOLEAN DEFAULT TRUE,
    is_primary_key   BOOLEAN DEFAULT FALSE,
    is_foreign_key   BOOLEAN DEFAULT FALSE,
    description      TEXT,
    metadata         JSONB,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(catalog_id, name)
);

CREATE INDEX IF NOT EXISTS idx_columns_catalog      ON columns(catalog_id);
CREATE INDEX IF NOT EXISTS idx_columns_name         ON columns(name);               -- added: search by column name
CREATE INDEX IF NOT EXISTS idx_columns_data_type    ON columns(data_type);          -- added: filter by type
CREATE INDEX IF NOT EXISTS idx_columns_primary_key  ON columns(is_primary_key)
    WHERE is_primary_key = TRUE;                                                    -- added: partial index for PKs
CREATE INDEX IF NOT EXISTS idx_columns_foreign_key  ON columns(is_foreign_key)
    WHERE is_foreign_key = TRUE;                                                    -- added: partial index for FKs

-- -- ============================================================================
-- -- RELATIONSHIPS (legacy lineage)
-- -- ============================================================================

-- CREATE TABLE IF NOT EXISTS relationships (
--     id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     source_catalog_id  UUID REFERENCES catalogs(id) ON DELETE CASCADE,
--     target_catalog_id  UUID REFERENCES catalogs(id) ON DELETE CASCADE,
--     relationship_type  VARCHAR(50) DEFAULT 'dependency',
--     metadata           JSONB,
--     created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_catalog_id);  -- added
-- CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_catalog_id);  -- added

-- ============================================================================
-- CUSTOM PROPERTIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS custom_properties (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id UUID REFERENCES catalogs(id) ON DELETE CASCADE,
    key        VARCHAR(255) NOT NULL,
    value      TEXT,
    value_type VARCHAR(50) DEFAULT 'string',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(catalog_id, key)
);

CREATE INDEX IF NOT EXISTS idx_custom_props_catalog ON custom_properties(catalog_id);  -- added

-- ============================================================================
-- DOMAINS
-- ============================================================================

CREATE TABLE IF NOT EXISTS domains (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name             VARCHAR(255) NOT NULL,
    description      TEXT,
    color            VARCHAR(20),
    parent_domain_id UUID REFERENCES domains(id) ON DELETE SET NULL,
    owner_id         UUID REFERENCES owners(id)  ON DELETE SET NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name)
);

-- Idempotent migration
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='domains' AND column_name='owner_id') THEN
        ALTER TABLE domains ADD COLUMN owner_id UUID REFERENCES owners(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_domains_parent ON domains(parent_domain_id);  -- added: hierarchical traversal
CREATE INDEX IF NOT EXISTS idx_domains_owner  ON domains(owner_id);          -- added

DROP TRIGGER IF EXISTS update_domains_updated_at ON domains;
CREATE TRIGGER update_domains_updated_at
    BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DOMAIN <-> CATALOG ASSIGNMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain_catalog_assignments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id   UUID NOT NULL REFERENCES domains(id)  ON DELETE CASCADE,
    catalog_id  UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by VARCHAR(255) DEFAULT 'system',
    UNIQUE(domain_id, catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_domain_catalog_domain  ON domain_catalog_assignments(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_catalog_catalog ON domain_catalog_assignments(catalog_id);

-- ============================================================================
-- API ACTIVITY LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_logs (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint         VARCHAR(255) NOT NULL,
    method           VARCHAR(10)  NOT NULL,
    action_summary   TEXT         NOT NULL,
    entity_type      VARCHAR(100),
    entity_id        VARCHAR(255),
    entity_name      VARCHAR(255),
    owner_id         UUID REFERENCES owners(id) ON DELETE SET NULL,
    status_code      INTEGER,
    request_body     JSONB,
    response_summary TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint    ON api_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at  ON api_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_entity_type ON api_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_api_logs_owner       ON api_logs(owner_id);          -- added: filter logs by owner

-- ============================================================================
-- CATALOG STATS
-- ============================================================================

CREATE TABLE IF NOT EXISTS catalog_stats (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id   UUID REFERENCES catalogs(id)      ON DELETE CASCADE,
    source_id    UUID REFERENCES data_sources(id)  ON DELETE CASCADE,
    row_count    BIGINT  DEFAULT 0,
    column_count INTEGER DEFAULT 0,
    computed_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_catalog_stats_catalog ON catalog_stats(catalog_id);
CREATE INDEX IF NOT EXISTS idx_catalog_stats_source  ON catalog_stats(source_id);

-- ============================================================================
-- TAGS
-- ============================================================================


-- Base table
CREATE TABLE IF NOT EXISTS tags (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    color       VARCHAR(20),
    owner_id    UUID REFERENCES owners(id) ON DELETE SET NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

----------------------------------------------------
-- Ensure owner_id exists (safe migration)
----------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='tags' AND column_name='owner_id'
    ) THEN
        ALTER TABLE tags
        ADD COLUMN owner_id UUID REFERENCES owners(id) ON DELETE SET NULL;
    END IF;
END $$;

----------------------------------------------------
-- Add tag_type
----------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='tags' AND column_name='tag_type'
    ) THEN
        ALTER TABLE tags
        ADD COLUMN tag_type VARCHAR(50);
    END IF;
END $$;

----------------------------------------------------
-- Add security_policy
----------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='tags' AND column_name='security_policy'
    ) THEN
        ALTER TABLE tags
        ADD COLUMN security_policy VARCHAR(50);
    END IF;
END $$;

----------------------------------------------------
-- Add status
----------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='tags' AND column_name='status'
    ) THEN
        ALTER TABLE tags
        ADD COLUMN status VARCHAR(20) DEFAULT 'active';
    END IF;
END $$;

----------------------------------------------------
-- Add constraints (only if not exists)
----------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'check_tag_type'
    ) THEN
        ALTER TABLE tags
        ADD CONSTRAINT check_tag_type
        CHECK (tag_type IN ('privacy','classification','retention','general'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'check_tag_status'
    ) THEN
        ALTER TABLE tags
        ADD CONSTRAINT check_tag_status
        CHECK (status IN ('active','inactive'));
    END IF;
END $$;

----------------------------------------------------
-- Indexes
----------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_tags_name   ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_owner  ON tags(owner_id);
CREATE INDEX IF NOT EXISTS idx_tags_type   ON tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_tags_status ON tags(status);

----------------------------------------------------
-- Auto update timestamp trigger
----------------------------------------------------

DROP TRIGGER IF EXISTS update_tags_updated_at ON tags;

CREATE TRIGGER update_tags_updated_at
BEFORE UPDATE ON tags
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();



-- ============================================================================
-- TAG <-> CATALOG ASSIGNMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_catalog_assignments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id      UUID NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
    catalog_id  UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by VARCHAR(255) DEFAULT 'system',
    UNIQUE(tag_id, catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_tag_catalog_tag     ON tag_catalog_assignments(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_catalog_catalog ON tag_catalog_assignments(catalog_id);

-- ============================================================================
-- TAG <-> COLUMN ASSIGNMENTS
-- (FIX: indexes were commented out – now properly enabled)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_column_assignments (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id           UUID NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
    column_id        UUID NOT NULL REFERENCES columns(id)  ON DELETE CASCADE,
    catalog_id       UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    confidence_score NUMERIC(3,2) DEFAULT 0.0,
    assigned_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by      VARCHAR(255) DEFAULT 'azure-ai',
    UNIQUE(tag_id, column_id)
);

-- These were incorrectly commented out — now restored:
CREATE INDEX IF NOT EXISTS idx_tca_catalog    ON tag_column_assignments(catalog_id);
CREATE INDEX IF NOT EXISTS idx_tca_column     ON tag_column_assignments(column_id);
CREATE INDEX IF NOT EXISTS idx_tca_tag        ON tag_column_assignments(tag_id);
CREATE INDEX IF NOT EXISTS idx_tca_confidence ON tag_column_assignments(confidence_score DESC);

-- ============================================================================
-- GLOSSARY GROUPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS glossary_groups (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id    UUID REFERENCES owners(id) ON DELETE SET NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name   = 'glossary_groups'
          AND column_name  = 'parent_group_id'
    ) THEN
        ALTER TABLE glossary_groups
            ADD COLUMN parent_group_id UUID REFERENCES glossary_groups(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_glossary_groups_parent ON glossary_groups(parent_group_id);
CREATE INDEX IF NOT EXISTS idx_glossary_groups_owner  ON glossary_groups(owner_id);
CREATE INDEX IF NOT EXISTS idx_glossary_groups_name   ON glossary_groups(name);  -- added: lookup by name

DROP TRIGGER IF EXISTS update_glossary_groups_updated_at ON glossary_groups;
CREATE TRIGGER update_glossary_groups_updated_at
    BEFORE UPDATE ON glossary_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- GLOSSARY TERMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS glossary_terms (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id    UUID REFERENCES owners(id) ON DELETE SET NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name   = 'glossary_terms'
          AND column_name  = 'parent_group_id'
    ) THEN
        ALTER TABLE glossary_terms
            ADD COLUMN parent_group_id UUID REFERENCES glossary_groups(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_glossary_terms_group ON glossary_terms(parent_group_id);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_owner ON glossary_terms(owner_id);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_name  ON glossary_terms(name);  -- added: lookup by name

DROP TRIGGER IF EXISTS update_glossary_terms_updated_at ON glossary_terms;
CREATE TRIGGER update_glossary_terms_updated_at
    BEFORE UPDATE ON glossary_terms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- GLOSSARY TERM ASSIGNMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS glossary_term_catalog_assignments (
    term_id     UUID NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,
    catalog_id  UUID NOT NULL REFERENCES catalogs(id)       ON DELETE CASCADE,
    assigned_by VARCHAR(255) DEFAULT 'system',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (term_id, catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_gtca_catalog ON glossary_term_catalog_assignments(catalog_id);
CREATE INDEX IF NOT EXISTS idx_gtca_term    ON glossary_term_catalog_assignments(term_id);  -- added

CREATE TABLE IF NOT EXISTS glossary_term_column_assignments (
    term_id     UUID NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,
    column_id   UUID NOT NULL REFERENCES columns(id)        ON DELETE CASCADE,
    assigned_by VARCHAR(255) DEFAULT 'system',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (term_id, column_id)
);

CREATE INDEX IF NOT EXISTS idx_gtcola_column ON glossary_term_column_assignments(column_id);
CREATE INDEX IF NOT EXISTS idx_gtcola_term   ON glossary_term_column_assignments(term_id);  -- added

-- ============================================================================
-- TABLE LINEAGE
-- ============================================================================

CREATE TABLE IF NOT EXISTS table_lineage (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upstream_catalog_id   UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    downstream_catalog_id UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    transformation_query  TEXT,
    owner_id              UUID REFERENCES owners(id) ON DELETE SET NULL,
    is_active             BOOLEAN DEFAULT TRUE,
    created_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_table_lineage UNIQUE (upstream_catalog_id, downstream_catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_tl_upstream   ON table_lineage(upstream_catalog_id);
CREATE INDEX IF NOT EXISTS idx_tl_downstream ON table_lineage(downstream_catalog_id);
CREATE INDEX IF NOT EXISTS idx_tl_owner      ON table_lineage(owner_id);
CREATE INDEX IF NOT EXISTS idx_tl_active     ON table_lineage(is_active);
CREATE INDEX IF NOT EXISTS idx_tl_created_at ON table_lineage(created_at DESC);  -- added: latest lineage first

DROP TRIGGER IF EXISTS update_table_lineage_updated_at ON table_lineage;
CREATE TRIGGER update_table_lineage_updated_at
    BEFORE UPDATE ON table_lineage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- LINEAGE COLUMN MAPPINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS lineage_column_mappings (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lineage_id           UUID NOT NULL REFERENCES table_lineage(id) ON DELETE CASCADE,
    upstream_column_id   UUID NOT NULL REFERENCES columns(id)       ON DELETE CASCADE,
    downstream_column_id UUID NOT NULL REFERENCES columns(id)       ON DELETE CASCADE,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_col_mapping UNIQUE (lineage_id, upstream_column_id, downstream_column_id)
);

CREATE INDEX IF NOT EXISTS idx_lcm_lineage   ON lineage_column_mappings(lineage_id);
CREATE INDEX IF NOT EXISTS idx_lcm_up_col    ON lineage_column_mappings(upstream_column_id);
CREATE INDEX IF NOT EXISTS idx_lcm_down_col  ON lineage_column_mappings(downstream_column_id);



CREATE TABLE IF NOT EXISTS pii_detection_pending (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id        UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    entity_type      VARCHAR(10) NOT NULL CHECK (entity_type IN ('catalog','column')),
    catalog_id       UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    column_id        UUID REFERENCES columns(id) ON DELETE CASCADE,   -- NULL for catalog-level
    tag_id           UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    tag_name         VARCHAR(255) NOT NULL,
    confidence_score NUMERIC(4,3) DEFAULT 0.0,
    is_sensitive     BOOLEAN DEFAULT FALSE,
    data_type        VARCHAR(100),
    reasoning        TEXT,
    suggested_by     VARCHAR(255) DEFAULT 'ai-auto',
    suggested_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by      VARCHAR(255),
    reviewed_at      TIMESTAMP WITH TIME ZONE,
    status           VARCHAR(20) DEFAULT 'pending'
                         CHECK (status IN ('pending','approved','rejected')),

    -- unique constraint used for upsert — coalesce column_id to catalog_id
    -- when null so the expression is never NULL
    column_id_or_null UUID GENERATED ALWAYS AS (
        COALESCE(column_id, catalog_id)
    ) STORED,
    UNIQUE (entity_type, catalog_id, column_id_or_null, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_pii_pending_source  ON pii_detection_pending(source_id);
CREATE INDEX IF NOT EXISTS idx_pii_pending_status  ON pii_detection_pending(status);
CREATE INDEX IF NOT EXISTS idx_pii_pending_catalog ON pii_detection_pending(catalog_id);
CREATE INDEX IF NOT EXISTS idx_pii_pending_column  ON pii_detection_pending(column_id);


CREATE TABLE IF NOT EXISTS job_logs (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id     UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    source_id  UUID NOT NULL REFERENCES data_sources(id)   ON DELETE CASCADE,
    level      VARCHAR(10) NOT NULL
                   CHECK (level IN ('error', 'warning', 'success')),
    message    TEXT        NOT NULL,
    logged_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fast lookup: all logs for a source ordered by time (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_job_logs_source_time
    ON job_logs (source_id, logged_at DESC);

-- Fast lookup: all logs for a specific job
CREATE INDEX IF NOT EXISTS idx_job_logs_job
    ON job_logs (job_id, logged_at DESC);

-- Fast lookup: filter by level within a source
CREATE INDEX IF NOT EXISTS idx_job_logs_level
    ON job_logs (source_id, level, logged_at DESC);




----------------------------------------------------------
--compliance snapshot
----------------------------------------------------------

CREATE TABLE IF NOT EXISTS compliance_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recorded_at             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Overall Compliance Metrics
    overall_score                   NUMERIC(5,2) NOT NULL,
    overall_health_status           VARCHAR(20)  NOT NULL,
    overall_change_from_last_month  NUMERIC(5,2),

    -- Framework Scores
    gdpr_score          NUMERIC(5,2),
    gdpr_status         VARCHAR(20),
    gdpr_rules_passed   INTEGER,
    gdpr_rules_total    INTEGER,
    gdpr_last_checked   TEXT,

    soc2_score          NUMERIC(5,2),
    soc2_status         VARCHAR(20),
    soc2_rules_passed   INTEGER,
    soc2_rules_total    INTEGER,
    soc2_last_checked   TEXT,

    hipaa_score         NUMERIC(5,2),
    hipaa_status        VARCHAR(20),
    hipaa_rules_passed  INTEGER,
    hipaa_rules_total   INTEGER,
    hipaa_last_checked  TEXT,

    dpa_score           NUMERIC(5,2),
    dpa_status          VARCHAR(20),
    dpa_rules_passed    INTEGER,
    dpa_rules_total     INTEGER,
    dpa_last_checked    TEXT,

    irr_score           NUMERIC(5,2),
    irr_status          VARCHAR(20),
    irr_rules_passed    INTEGER,
    irr_rules_total     INTEGER,
    irr_last_checked    TEXT,

    psa_score           NUMERIC(5,2),
    psa_status          VARCHAR(20),
    psa_rules_passed    INTEGER,
    psa_rules_total     INTEGER,
    psa_last_checked    TEXT,

    -- Issue Counts
    open_issues_count       INTEGER DEFAULT 0,
    critical_issues_count   INTEGER DEFAULT 0,
    high_issues_count       INTEGER DEFAULT 0,
    medium_issues_count     INTEGER DEFAULT 0,
    low_issues_count        INTEGER DEFAULT 0,

    -- Compliance Health
    compliance_health_score         NUMERIC(5,2),
    compliance_health_trend_label   TEXT,

    -- Top Issues
    top_issue_1_issue       TEXT,
    top_issue_1_framework   VARCHAR(20),
    top_issue_1_severity    VARCHAR(20),
    top_issue_1_dataset     TEXT,
    top_issue_1_assignee    TEXT,
    top_issue_1_due_date    TEXT,

    top_issue_2_issue       TEXT,
    top_issue_2_framework   VARCHAR(20),
    top_issue_2_severity    VARCHAR(20),
    top_issue_2_dataset     TEXT,
    top_issue_2_assignee    TEXT,
    top_issue_2_due_date    TEXT,

    top_issue_3_issue       TEXT,
    top_issue_3_framework   VARCHAR(20),
    top_issue_3_severity    VARCHAR(20),
    top_issue_3_dataset     TEXT,
    top_issue_3_assignee    TEXT,
    top_issue_3_due_date    TEXT,

    -- AI Insights
    ai_insights_text        TEXT,
    ai_insights_beta        BOOLEAN DEFAULT TRUE,

    -- Trend Data
    trend_month_label       TEXT,
    trend_overall_data      NUMERIC(5,2)[],
    trend_gdpr_data         NUMERIC(5,2)[],
    trend_soc2_data         NUMERIC(5,2)[],
    trend_hipaa_data        NUMERIC(5,2)[],
    trend_dpa_data          NUMERIC(5,2)[],
    trend_irr_data          NUMERIC(5,2)[],
    trend_psa_data          NUMERIC(5,2)[],

    -- Performance Metrics
    scan_duration_seconds   NUMERIC(8,2),

    -- Full Snapshot Backup
    snapshot_json           JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_recorded_at
    ON compliance_snapshots (recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_overall
    ON compliance_snapshots (overall_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_health
    ON compliance_snapshots (overall_health_status);

CREATE INDEX IF NOT EXISTS idx_snapshots_gdpr
    ON compliance_snapshots (gdpr_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_soc2
    ON compliance_snapshots (soc2_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_hipaa
    ON compliance_snapshots (hipaa_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_dpa
    ON compliance_snapshots (dpa_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_irr
    ON compliance_snapshots (irr_score);

CREATE INDEX IF NOT EXISTS idx_snapshots_psa
    ON compliance_snapshots (psa_score);


-----------------------------------------------------------------
---DATA CARD----
-----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS datacards (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_id   TEXT NOT NULL,
    table_name   TEXT,
    full_name    TEXT,
    data_card    TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status       TEXT NOT NULL DEFAULT 'generated',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_datacards_catalog UNIQUE (catalog_id)
);


-- ============================================================================
-- CATALOG QUERIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS catalog_queries (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    catalog_id  UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    query_text  TEXT NOT NULL,
    owner_id    UUID REFERENCES owners(id) ON DELETE SET NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_queries_catalog   ON catalog_queries(catalog_id);
CREATE INDEX IF NOT EXISTS idx_catalog_queries_owner     ON catalog_queries(owner_id);
CREATE INDEX IF NOT EXISTS idx_catalog_queries_created   ON catalog_queries(created_at DESC);

DROP TRIGGER IF EXISTS update_catalog_queries_updated_at ON catalog_queries;
CREATE TRIGGER update_catalog_queries_updated_at
    BEFORE UPDATE ON catalog_queries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();