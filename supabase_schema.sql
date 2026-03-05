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
    authenticity_reasoning      TEXT,
    improvement_suggestion      TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    UNIQUE(case_id, navigator_id)
);

-- ── 4. eval_format_1_timeline ───────────────────────────────────────────────
CREATE TABLE eval_format_1_timeline (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                      UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    case_label                      TEXT,
    navigator_name                  TEXT,
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
    case_label                  TEXT,
    navigator_name              TEXT,
    triple_index                INT NOT NULL,
    tactical_viability_score    INT NOT NULL CHECK (tactical_viability_score BETWEEN 1 AND 5)
);

-- ── 6. eval_format_3_boundaries ─────────────────────────────────────────────
CREATE TABLE eval_format_3_boundaries (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    case_label              TEXT,
    navigator_name          TEXT,
    option_index            INT NOT NULL,
    pn_category             TEXT NOT NULL,
    ai_intended_category    TEXT NOT NULL
);


-- ============================================================================
-- V3 TABLES (Round 2 — updated prompts, parallel to original tables)
-- Original tables above are preserved with Round 1 evaluation data.
-- ============================================================================

-- ── 7. synthetic_cases_v3 ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS synthetic_cases_v3 (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id                TEXT,
    label                   TEXT,
    narrative_summary       TEXT,
    format_1_state_log      JSONB,
    format_2_triples        JSONB,
    format_3_rl_scenario    JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 8. evaluation_sessions_v3 ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluation_sessions_v3 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                     UUID NOT NULL REFERENCES synthetic_cases_v3(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_id                UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    navigator_name              TEXT,
    status                      TEXT NOT NULL DEFAULT 'in_progress'
                                CHECK (status IN ('in_progress', 'completed')),
    overall_field_authenticity  INT CHECK (overall_field_authenticity BETWEEN 1 AND 5),
    authenticity_reasoning      TEXT,
    improvement_suggestion      TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    UNIQUE(case_id, navigator_id)
);

-- ── 9. eval_format_1_timeline_v3 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_1_timeline_v3 (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                      UUID NOT NULL REFERENCES evaluation_sessions_v3(id) ON DELETE CASCADE,
    case_label                      TEXT,
    navigator_name                  TEXT,
    event_index                     INT NOT NULL,
    clinical_impact                 TEXT NOT NULL,
    environmental_impact            TEXT NOT NULL,
    home_service_adoption_impact    TEXT NOT NULL,
    edd_delta                       TEXT NOT NULL,
    bottleneck_realism              BOOLEAN NOT NULL
);

-- ── 10. eval_format_2_tactics_v3 ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_2_tactics_v3 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                  UUID NOT NULL REFERENCES evaluation_sessions_v3(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_name              TEXT,
    triple_index                INT NOT NULL,
    tactical_viability_score    INT NOT NULL CHECK (tactical_viability_score BETWEEN 1 AND 5)
);

-- ── 11. eval_format_3_boundaries_v3 ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_3_boundaries_v3 (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES evaluation_sessions_v3(id) ON DELETE CASCADE,
    case_label              TEXT,
    navigator_name          TEXT,
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


-- ============================================================================
-- V3 TABLE RLS POLICIES
-- ============================================================================

ALTER TABLE synthetic_cases_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_sessions_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_1_timeline_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_2_tactics_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_3_boundaries_v3 ENABLE ROW LEVEL SECURITY;

-- synthetic_cases_v3
DROP POLICY IF EXISTS "Admins full access on synthetic_cases_v3" ON synthetic_cases_v3;
CREATE POLICY "Admins full access on synthetic_cases_v3"
    ON synthetic_cases_v3 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators read synthetic_cases_v3" ON synthetic_cases_v3;
CREATE POLICY "Navigators read synthetic_cases_v3"
    ON synthetic_cases_v3 FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'navigator'));

-- evaluation_sessions_v3
DROP POLICY IF EXISTS "Admins full access on evaluation_sessions_v3" ON evaluation_sessions_v3;
CREATE POLICY "Admins full access on evaluation_sessions_v3"
    ON evaluation_sessions_v3 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own sessions v3" ON evaluation_sessions_v3;
CREATE POLICY "Navigators manage own sessions v3"
    ON evaluation_sessions_v3 FOR ALL
    USING (navigator_id = auth.uid())
    WITH CHECK (navigator_id = auth.uid());

-- eval_format_1_timeline_v3
DROP POLICY IF EXISTS "Admins full access on eval_format_1_timeline_v3" ON eval_format_1_timeline_v3;
CREATE POLICY "Admins full access on eval_format_1_timeline_v3"
    ON eval_format_1_timeline_v3 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f1 evals v3" ON eval_format_1_timeline_v3;
CREATE POLICY "Navigators manage own f1 evals v3"
    ON eval_format_1_timeline_v3 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_1_timeline_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_1_timeline_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()));

-- eval_format_2_tactics_v3
DROP POLICY IF EXISTS "Admins full access on eval_format_2_tactics_v3" ON eval_format_2_tactics_v3;
CREATE POLICY "Admins full access on eval_format_2_tactics_v3"
    ON eval_format_2_tactics_v3 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f2 evals v3" ON eval_format_2_tactics_v3;
CREATE POLICY "Navigators manage own f2 evals v3"
    ON eval_format_2_tactics_v3 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_2_tactics_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_2_tactics_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()));

-- eval_format_3_boundaries_v3
DROP POLICY IF EXISTS "Admins full access on eval_format_3_boundaries_v3" ON eval_format_3_boundaries_v3;
CREATE POLICY "Admins full access on eval_format_3_boundaries_v3"
    ON eval_format_3_boundaries_v3 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f3 evals v3" ON eval_format_3_boundaries_v3;
CREATE POLICY "Navigators manage own f3 evals v3"
    ON eval_format_3_boundaries_v3 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_3_boundaries_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v3 WHERE evaluation_sessions_v3.id = eval_format_3_boundaries_v3.session_id AND evaluation_sessions_v3.navigator_id = auth.uid()));


-- ============================================================================
-- V4 TABLES (Round 3 — "Support, Suggest, Escalate" mentality overhaul)
-- V3 tables above are preserved with Round 2 evaluation data.
-- ============================================================================

-- ── 12. synthetic_cases_v4 ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS synthetic_cases_v4 (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id                        TEXT,
    label                           TEXT,
    narrative_summary               TEXT,
    boundary_planning_scratchpad    TEXT,
    format_1_state_log              JSONB,
    format_2_triples                JSONB,
    format_3_rl_scenario            JSONB,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 13. evaluation_sessions_v4 ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluation_sessions_v4 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                     UUID NOT NULL REFERENCES synthetic_cases_v4(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_id                UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    navigator_name              TEXT,
    status                      TEXT NOT NULL DEFAULT 'in_progress'
                                CHECK (status IN ('in_progress', 'completed')),
    overall_field_authenticity  INT CHECK (overall_field_authenticity BETWEEN 1 AND 5),
    authenticity_reasoning      TEXT,
    improvement_suggestion      TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    UNIQUE(case_id, navigator_id)
);

-- ── 14. eval_format_1_timeline_v4 ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_1_timeline_v4 (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                      UUID NOT NULL REFERENCES evaluation_sessions_v4(id) ON DELETE CASCADE,
    case_label                      TEXT,
    navigator_name                  TEXT,
    event_index                     INT NOT NULL,
    clinical_impact                 TEXT NOT NULL,
    environmental_impact            TEXT NOT NULL,
    home_service_adoption_impact    TEXT NOT NULL,
    edd_delta                       TEXT NOT NULL,
    bottleneck_realism              BOOLEAN NOT NULL
);

-- ── 15. eval_format_2_tactics_v4 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_2_tactics_v4 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                  UUID NOT NULL REFERENCES evaluation_sessions_v4(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_name              TEXT,
    triple_index                INT NOT NULL,
    tactical_viability_score    INT NOT NULL CHECK (tactical_viability_score BETWEEN 1 AND 5)
);

-- ── 16. eval_format_3_boundaries_v4 ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS eval_format_3_boundaries_v4 (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES evaluation_sessions_v4(id) ON DELETE CASCADE,
    case_label              TEXT,
    navigator_name          TEXT,
    option_index            INT NOT NULL,
    pn_category             TEXT NOT NULL,
    ai_intended_category    TEXT NOT NULL
);


-- ============================================================================
-- V4 TABLE RLS POLICIES
-- ============================================================================

ALTER TABLE synthetic_cases_v4 ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_sessions_v4 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_1_timeline_v4 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_2_tactics_v4 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_3_boundaries_v4 ENABLE ROW LEVEL SECURITY;

-- synthetic_cases_v4
DROP POLICY IF EXISTS "Admins full access on synthetic_cases_v4" ON synthetic_cases_v4;
CREATE POLICY "Admins full access on synthetic_cases_v4"
    ON synthetic_cases_v4 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators read synthetic_cases_v4" ON synthetic_cases_v4;
CREATE POLICY "Navigators read synthetic_cases_v4"
    ON synthetic_cases_v4 FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'navigator'));

-- evaluation_sessions_v4
DROP POLICY IF EXISTS "Admins full access on evaluation_sessions_v4" ON evaluation_sessions_v4;
CREATE POLICY "Admins full access on evaluation_sessions_v4"
    ON evaluation_sessions_v4 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own sessions v4" ON evaluation_sessions_v4;
CREATE POLICY "Navigators manage own sessions v4"
    ON evaluation_sessions_v4 FOR ALL
    USING (navigator_id = auth.uid())
    WITH CHECK (navigator_id = auth.uid());

-- eval_format_1_timeline_v4
DROP POLICY IF EXISTS "Admins full access on eval_format_1_timeline_v4" ON eval_format_1_timeline_v4;
CREATE POLICY "Admins full access on eval_format_1_timeline_v4"
    ON eval_format_1_timeline_v4 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f1 evals v4" ON eval_format_1_timeline_v4;
CREATE POLICY "Navigators manage own f1 evals v4"
    ON eval_format_1_timeline_v4 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_1_timeline_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_1_timeline_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()));

-- eval_format_2_tactics_v4
DROP POLICY IF EXISTS "Admins full access on eval_format_2_tactics_v4" ON eval_format_2_tactics_v4;
CREATE POLICY "Admins full access on eval_format_2_tactics_v4"
    ON eval_format_2_tactics_v4 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f2 evals v4" ON eval_format_2_tactics_v4;
CREATE POLICY "Navigators manage own f2 evals v4"
    ON eval_format_2_tactics_v4 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_2_tactics_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_2_tactics_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()));

-- eval_format_3_boundaries_v4
DROP POLICY IF EXISTS "Admins full access on eval_format_3_boundaries_v4" ON eval_format_3_boundaries_v4;
CREATE POLICY "Admins full access on eval_format_3_boundaries_v4"
    ON eval_format_3_boundaries_v4 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f3 evals v4" ON eval_format_3_boundaries_v4;
CREATE POLICY "Navigators manage own f3 evals v4"
    ON eval_format_3_boundaries_v4 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_3_boundaries_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v4 WHERE evaluation_sessions_v4.id = eval_format_3_boundaries_v4.session_id AND evaluation_sessions_v4.navigator_id = auth.uid()));


-- ============================================================================
-- V5 TABLES (Round 4 — Atlantis 3-Stage Lifecycle, LTC Filter, SW Boundary)
-- V4 tables above are preserved with Round 3 evaluation data.
-- ============================================================================

CREATE TABLE IF NOT EXISTS synthetic_cases_v5 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id                    TEXT,
    label                       TEXT,
    -- Stage 1: Entry & Triage
    atlantis_entry_confirmed    BOOLEAN,
    demographic_audit_note      TEXT,
    home_vs_ltc_determination   TEXT,
    -- Stage 2: Maintenance & Engagement
    weekly_facility_update      TEXT,
    v_card_and_flyer_status     TEXT,
    -- Stage 3: Handoff & Success Verification
    pre_dc_pulse_call_result    TEXT,
    atlantis_final_sync         TEXT,
    ma_visit_booking            TEXT,
    -- Core content
    narrative_summary           TEXT,
    format_1_state_log          JSONB,
    format_2_triples            JSONB,
    format_3_rl_scenario        JSONB,
    case_outcome                TEXT CHECK (case_outcome IN (
        'Success_Home_with_First_Visit',
        'Neutral_LTC_Closure',
        'Neutral_Alternative_Agency',
        'Failure_Transition_Breakdown'
    )),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluation_sessions_v5 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id                     UUID NOT NULL REFERENCES synthetic_cases_v5(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_id                UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    navigator_name              TEXT,
    status                      TEXT NOT NULL DEFAULT 'in_progress'
                                CHECK (status IN ('in_progress', 'completed')),
    overall_field_authenticity  INT CHECK (overall_field_authenticity BETWEEN 1 AND 5),
    authenticity_reasoning      TEXT,
    improvement_suggestion      TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                TIMESTAMPTZ,
    UNIQUE(case_id, navigator_id)
);

CREATE TABLE IF NOT EXISTS eval_format_1_timeline_v5 (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                      UUID NOT NULL REFERENCES evaluation_sessions_v5(id) ON DELETE CASCADE,
    case_label                      TEXT,
    navigator_name                  TEXT,
    event_index                     INT NOT NULL,
    clinical_impact                 TEXT NOT NULL,
    environmental_impact            TEXT NOT NULL,
    home_service_adoption_impact    TEXT NOT NULL,
    edd_delta                       TEXT NOT NULL,
    bottleneck_realism              BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_format_2_tactics_v5 (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id                  UUID NOT NULL REFERENCES evaluation_sessions_v5(id) ON DELETE CASCADE,
    case_label                  TEXT,
    navigator_name              TEXT,
    triple_index                INT NOT NULL,
    tactical_viability_score    INT NOT NULL CHECK (tactical_viability_score BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS eval_format_3_boundaries_v5 (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES evaluation_sessions_v5(id) ON DELETE CASCADE,
    case_label              TEXT,
    navigator_name          TEXT,
    option_index            INT NOT NULL,
    pn_category             TEXT NOT NULL,
    ai_intended_category    TEXT NOT NULL
);


-- ============================================================================
-- V5 TABLE RLS POLICIES
-- ============================================================================

ALTER TABLE synthetic_cases_v5 ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_sessions_v5 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_1_timeline_v5 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_2_tactics_v5 ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_format_3_boundaries_v5 ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins full access on synthetic_cases_v5" ON synthetic_cases_v5;
CREATE POLICY "Admins full access on synthetic_cases_v5"
    ON synthetic_cases_v5 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators read synthetic_cases_v5" ON synthetic_cases_v5;
CREATE POLICY "Navigators read synthetic_cases_v5"
    ON synthetic_cases_v5 FOR SELECT
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'navigator'));

DROP POLICY IF EXISTS "Admins full access on evaluation_sessions_v5" ON evaluation_sessions_v5;
CREATE POLICY "Admins full access on evaluation_sessions_v5"
    ON evaluation_sessions_v5 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own sessions v5" ON evaluation_sessions_v5;
CREATE POLICY "Navigators manage own sessions v5"
    ON evaluation_sessions_v5 FOR ALL
    USING (navigator_id = auth.uid())
    WITH CHECK (navigator_id = auth.uid());

DROP POLICY IF EXISTS "Admins full access on eval_format_1_timeline_v5" ON eval_format_1_timeline_v5;
CREATE POLICY "Admins full access on eval_format_1_timeline_v5"
    ON eval_format_1_timeline_v5 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f1 evals v5" ON eval_format_1_timeline_v5;
CREATE POLICY "Navigators manage own f1 evals v5"
    ON eval_format_1_timeline_v5 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_1_timeline_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_1_timeline_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()));

DROP POLICY IF EXISTS "Admins full access on eval_format_2_tactics_v5" ON eval_format_2_tactics_v5;
CREATE POLICY "Admins full access on eval_format_2_tactics_v5"
    ON eval_format_2_tactics_v5 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f2 evals v5" ON eval_format_2_tactics_v5;
CREATE POLICY "Navigators manage own f2 evals v5"
    ON eval_format_2_tactics_v5 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_2_tactics_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_2_tactics_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()));

DROP POLICY IF EXISTS "Admins full access on eval_format_3_boundaries_v5" ON eval_format_3_boundaries_v5;
CREATE POLICY "Admins full access on eval_format_3_boundaries_v5"
    ON eval_format_3_boundaries_v5 FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Navigators manage own f3 evals v5" ON eval_format_3_boundaries_v5;
CREATE POLICY "Navigators manage own f3 evals v5"
    ON eval_format_3_boundaries_v5 FOR ALL
    USING (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_3_boundaries_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM evaluation_sessions_v5 WHERE evaluation_sessions_v5.id = eval_format_3_boundaries_v5.session_id AND evaluation_sessions_v5.navigator_id = auth.uid()));
