-- ============================================================================
-- Data Annotation Platform: Supabase Schema (Full Reset)
-- Safe to re-run: drops and recreates all tables, policies, and functions.
-- Run this entire script in Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DROP EXISTING TABLES (in FK order)
-- ============================================================================

DROP TABLE IF EXISTS eval_format_3_boundaries CASCADE;
DROP TABLE IF EXISTS eval_format_2_tactics CASCADE;
DROP TABLE IF EXISTS eval_format_1_timeline CASCADE;
DROP TABLE IF EXISTS evaluation_sessions CASCADE;
DROP TABLE IF EXISTS synthetic_cases CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- ============================================================================
-- CREATE TABLES
-- ============================================================================

-- ── 1. profiles ─────────────────────────────────────────────────────────────
CREATE TABLE profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('admin', 'navigator')),
    full_name   TEXT NOT NULL,
    pin         TEXT CHECK (char_length(pin) = 4 AND pin ~ '^\d{4}$'),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 2. synthetic_cases ──────────────────────────────────────────────────────
CREATE TABLE synthetic_cases (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id                TEXT,
    label                   TEXT,
    narrative_summary       TEXT,
    format_1_state_log      JSONB,
    format_2_triples        JSONB,
    format_3_rl_scenario    JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 3. evaluation_sessions ──────────────────────────────────────────────────
CREATE TABLE evaluation_sessions (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                     UUID NOT NULL REFERENCES synthetic_cases(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_id                UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    navigator_name              TEXT,
    status                      TEXT NOT NULL DEFAULT 'in_progress'
                                CHECK (status IN ('in_progress', 'completed')),
    overall_field_authenticity  INT CHECK (overall_field_authenticity BETWEEN 1 AND 5),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    UNIQUE(case_id, navigator_id)
);

-- ── 4. eval_format_1_timeline ───────────────────────────────────────────────
CREATE TABLE eval_format_1_timeline (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                      UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    event_index                     INT NOT NULL,
    clinical_impact                 TEXT NOT NULL,
    environmental_impact            TEXT NOT NULL,
    home_service_adoption_impact    TEXT NOT NULL,
    edd_delta                       TEXT NOT NULL,
    bottleneck_realism              BOOLEAN NOT NULL
);

-- ── 5. eval_format_2_tactics ────────────────────────────────────────────────
CREATE TABLE eval_format_2_tactics (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                  UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    triple_index                INT NOT NULL,
    intent_feasibility_score    INT NOT NULL CHECK (intent_feasibility_score BETWEEN 1 AND 5)
);

-- ── 6. eval_format_3_boundaries ─────────────────────────────────────────────
CREATE TABLE eval_format_3_boundaries (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    option_index            INT NOT NULL,
    pn_category             TEXT NOT NULL,
    ai_intended_category    TEXT NOT NULL
);


-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthetic_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_1_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_2_tactics ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_3_boundaries ENABLE ROW LEVEL SECURITY;

-- Helper function: check if the current user is an admin
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;


-- ── profiles policies ───────────────────────────────────────────────────────

CREATE POLICY "Admins full access on profiles"
    ON profiles FOR ALL
    USING (public.is_admin());

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Navigators read own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);


-- ── synthetic_cases policies ────────────────────────────────────────────────

CREATE POLICY "Admins full access on synthetic_cases"
    ON synthetic_cases FOR ALL
    USING (public.is_admin());

CREATE POLICY "Navigators read synthetic_cases"
    ON synthetic_cases FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'navigator')
    );


-- ── evaluation_sessions policies ────────────────────────────────────────────

CREATE POLICY "Admins full access on evaluation_sessions"
    ON evaluation_sessions FOR ALL
    USING (public.is_admin());

CREATE POLICY "Navigators manage own sessions"
    ON evaluation_sessions FOR ALL
    USING (navigator_id = auth.uid())
    WITH CHECK (navigator_id = auth.uid());


-- ── eval_format_1_timeline policies ─────────────────────────────────────────

CREATE POLICY "Admins full access on eval_format_1_timeline"
    ON eval_format_1_timeline FOR ALL
    USING (public.is_admin());

CREATE POLICY "Navigators manage own f1 evals"
    ON eval_format_1_timeline FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_1_timeline.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_1_timeline.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    );


-- ── eval_format_2_tactics policies ──────────────────────────────────────────

CREATE POLICY "Admins full access on eval_format_2_tactics"
    ON eval_format_2_tactics FOR ALL
    USING (public.is_admin());

CREATE POLICY "Navigators manage own f2 evals"
    ON eval_format_2_tactics FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_2_tactics.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_2_tactics.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    );


-- ── eval_format_3_boundaries policies ───────────────────────────────────────

CREATE POLICY "Admins full access on eval_format_3_boundaries"
    ON eval_format_3_boundaries FOR ALL
    USING (public.is_admin());

CREATE POLICY "Navigators manage own f3 evals"
    ON eval_format_3_boundaries FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_3_boundaries.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM evaluation_sessions
            WHERE evaluation_sessions.id = eval_format_3_boundaries.session_id
            AND evaluation_sessions.navigator_id = auth.uid()
        )
    );
