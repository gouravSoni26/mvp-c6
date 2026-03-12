-- ============================================================
-- PostgreSQL schema for Supabase
-- Run this in Supabase SQL Editor to create all tables
-- ============================================================

-- Table 1: learning_context (single-row user preferences)
CREATE TABLE learning_context (
    id INTEGER PRIMARY KEY DEFAULT 1,
    learning_goals TEXT NOT NULL DEFAULT '',
    digest_format TEXT NOT NULL DEFAULT 'top_3',
    learning_style TEXT NOT NULL DEFAULT 'build_first',
    depth_preference TEXT NOT NULL DEFAULT 'mixed_with_flags',
    consumption_habits TEXT NOT NULL DEFAULT 'mixed',
    skill_levels JSONB NOT NULL DEFAULT '{}'::jsonb,
    time_availability TEXT NOT NULL DEFAULT '30 mins/day',
    project_context TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO learning_context (id) VALUES (1);

-- Table 2: sources (content feed sources)
CREATE TABLE sources (
    id BIGSERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 3: items (individual content pieces)
CREATE TABLE items (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT REFERENCES sources(id),
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    author TEXT,
    summary TEXT,
    url TEXT NOT NULL,
    source_type TEXT,
    published_at TIMESTAMPTZ,
    relevance_score DOUBLE PRECISION,
    score_justification TEXT,
    included_in_digest BOOLEAN DEFAULT FALSE,
    digest_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_items_relevance ON items(relevance_score DESC NULLS LAST);
CREATE INDEX idx_items_external_id ON items(external_id);

-- Table 4: feedback (user ratings on digest items)
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT REFERENCES items(id),
    rating TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_created ON feedback(created_at);

-- ============================================================
-- RPC Functions (for aggregate queries)
-- ============================================================

CREATE OR REPLACE FUNCTION get_precision(num_days INTEGER DEFAULT 7)
RETURNS TABLE(total BIGINT, useful BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total,
        COUNT(*) FILTER (WHERE f.rating = 'useful')::BIGINT AS useful
    FROM feedback f
    WHERE f.created_at >= NOW() - (num_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_daily_precision(num_days INTEGER DEFAULT 3)
RETURNS TABLE(day DATE, total BIGINT, useful BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.created_at::DATE AS day,
        COUNT(*)::BIGINT AS total,
        COUNT(*) FILTER (WHERE f.rating = 'useful')::BIGINT AS useful
    FROM feedback f
    WHERE f.created_at >= NOW() - (num_days || ' days')::INTERVAL
    GROUP BY f.created_at::DATE
    ORDER BY day DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Row Level Security (permissive — single-user app)
-- ============================================================
ALTER TABLE learning_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_all" ON learning_context FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all" ON sources FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all" ON items FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all" ON feedback FOR ALL USING (true) WITH CHECK (true);
