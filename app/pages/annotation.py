"""
Page D: Annotation Page — Core Evaluation UI

Displays the case narrative and renders evaluation forms for all 3 formats:
  Format 1: Timeline & Impact (per state_log event)
  Format 2: Tactical Library (per reasoning triple)
  Format 3: RL Scenarios (rank 1 vs rank 0)

On resume, loads previously saved answers from the database.
Save Progress writes answers without completing. Submit finalises.
"""

import streamlit as st
from datetime import datetime, timezone
from httpx import RemoteProtocolError
from app.supabase_client import get_authenticated_client


def _retry(fn, retries=2):
    """Retry a Supabase call on stale connection errors."""
    for attempt in range(retries):
        try:
            return fn()
        except RemoteProtocolError:
            if attempt == retries - 1:
                raise
            st.cache_resource.clear()

CLINICAL_ENV_OPTIONS = ["Improves", "Worsens", "Unchanged", "Unclear"]
SERVICE_ADOPTION_OPTIONS = ["Negative", "Positive", "Unclear", "Unchanged"]
EDD_DELTA_OPTIONS = [
    "+ >14 Days",
    "+ 7-14 Days",
    "+ 3-6 Days",
    "+ 0-2 Days",
    "- 0-2 Days",
    "- 3-6 Days",
    "- 7-14 Days",
    "- >14 Days",
]


def _load_saved_answers(client, session_id):
    """Fetch any previously saved evaluation answers for this session."""
    f1_resp = _retry(lambda: (
        client.table("eval_format_1_timeline")
        .select("*")
        .eq("session_id", session_id)
        .order("event_index")
        .execute()
    ))
    f2_resp = _retry(lambda: (
        client.table("eval_format_2_tactics")
        .select("*")
        .eq("session_id", session_id)
        .order("triple_index")
        .execute()
    ))
    f3_resp = _retry(lambda: (
        client.table("eval_format_3_boundaries")
        .select("*")
        .eq("session_id", session_id)
        .order("option_index")
        .execute()
    ))

    f1_saved = {row["event_index"]: row for row in (f1_resp.data or [])}
    f2_saved = {row["triple_index"]: row for row in (f2_resp.data or [])}
    f3_saved = {row["option_index"]: row for row in (f3_resp.data or [])}

    return f1_saved, f2_saved, f3_saved


def _save_answers(client, session_id, f1_inputs, f2_inputs, f3_inputs,
                   case_label="", navigator_name=""):
    """Save current answers to eval tables (delete old rows first)."""
    # Clear existing rows for this session
    client.table("eval_format_1_timeline").delete().eq("session_id", session_id).execute()
    client.table("eval_format_2_tactics").delete().eq("session_id", session_id).execute()
    client.table("eval_format_3_boundaries").delete().eq("session_id", session_id).execute()

    common = {"session_id": session_id, "case_label": case_label, "navigator_name": navigator_name}

    # Insert current answers
    if f1_inputs:
        f1_rows = [{**common, **inp} for inp in f1_inputs]
        client.table("eval_format_1_timeline").insert(f1_rows).execute()

    if f2_inputs:
        f2_rows = [{**common, **inp} for inp in f2_inputs]
        client.table("eval_format_2_tactics").insert(f2_rows).execute()

    if f3_inputs:
        f3_rows = [{**common, **inp} for inp in f3_inputs]
        client.table("eval_format_3_boundaries").insert(f3_rows).execute()


def render():
    client = get_authenticated_client()

    session_id = st.session_state.get("current_session_id")
    case_id = st.session_state.get("current_case_id")

    if not session_id or not case_id:
        st.error("No active evaluation session. Returning to dashboard.")
        st.session_state["current_page"] = "pn_dashboard"
        st.rerun()
        return

    if st.button("< Back to Dashboard"):
        st.session_state["current_page"] = "pn_dashboard"
        st.rerun()

    # ── Fetch case data ──────────────────────────────────────────────────────
    case_resp = (
        client.table("synthetic_cases")
        .select("*")
        .eq("id", case_id)
        .single()
        .execute()
    )
    case = case_resp.data

    # ── Get case_label and navigator_name from the session ───────────────────
    case_label = case.get("label", "")
    navigator_name = st.session_state.get("full_name", "")

    # ── Load any previously saved answers ─────────────────────────────────────
    f1_saved, f2_saved, f3_saved = _load_saved_answers(client, session_id)

    st.header("Case Narrative")
    st.info(case["narrative_summary"])

    state_log = case["format_1_state_log"]
    triples = case["format_2_triples"]
    rl_scenario = case["format_3_rl_scenario"]

    # ── FORMAT 1: Timeline & Impact ──────────────────────────────────────────
    st.header("Format 1: State Log Evaluation")
    f1_inputs = []

    for i, event in enumerate(state_log):
        saved = f1_saved.get(i, {})
        label = event["event_description"][:80]
        with st.expander(f"Event {i + 1}: {label}...", expanded=True):
            st.markdown(f"**Event Description:** {event['event_description']}")
            st.markdown(f"**AI Bot Assumed Bottleneck:** {event['ai_assumed_bottleneck']}")

            st.divider()
            st.subheader("Your Evaluation")

            col1, col2, col3 = st.columns(3)

            with col1:
                ci_default = 0
                if saved.get("clinical_impact") in CLINICAL_ENV_OPTIONS:
                    ci_default = CLINICAL_ENV_OPTIONS.index(saved["clinical_impact"])
                clinical_impact = st.selectbox(
                    "Clinical Impact",
                    CLINICAL_ENV_OPTIONS,
                    index=ci_default,
                    key=f"f1_clinical_{i}",
                )

            with col2:
                ei_default = 0
                if saved.get("environmental_impact") in CLINICAL_ENV_OPTIONS:
                    ei_default = CLINICAL_ENV_OPTIONS.index(saved["environmental_impact"])
                environmental_impact = st.selectbox(
                    "Environmental Impact",
                    CLINICAL_ENV_OPTIONS,
                    index=ei_default,
                    key=f"f1_env_{i}",
                )

            with col3:
                sa_default = 0
                if saved.get("home_service_adoption_impact") in SERVICE_ADOPTION_OPTIONS:
                    sa_default = SERVICE_ADOPTION_OPTIONS.index(saved["home_service_adoption_impact"])
                home_service_adoption = st.selectbox(
                    "Home Service Adoption Impact",
                    SERVICE_ADOPTION_OPTIONS,
                    index=sa_default,
                    key=f"f1_service_{i}",
                )

            edd_default = 0
            if saved.get("edd_delta") in EDD_DELTA_OPTIONS:
                edd_default = EDD_DELTA_OPTIONS.index(saved["edd_delta"])
            edd_delta = st.selectbox(
                "EDD Delta",
                EDD_DELTA_OPTIONS,
                index=edd_default,
                key=f"f1_edd_{i}",
            )

            bottleneck_default = 0 if saved.get("bottleneck_realism", True) else 1
            bottleneck_realism = st.radio(
                "Bottleneck Realistic?",
                ["True", "False"],
                index=bottleneck_default,
                key=f"f1_bottleneck_{i}",
                horizontal=True,
            )

            f1_inputs.append({
                "event_index": i,
                "clinical_impact": clinical_impact,
                "environmental_impact": environmental_impact,
                "home_service_adoption_impact": home_service_adoption,
                "edd_delta": edd_delta,
                "bottleneck_realism": bottleneck_realism == "True",
            })

    # ── FORMAT 2: Tactical Library ───────────────────────────────────────────
    st.header("Format 2: Reasoning Triples Evaluation")
    f2_inputs = []

    for i, triple in enumerate(triples):
        saved = f2_saved.get(i, {})
        label = triple["situation"][:80]
        with st.expander(f"Triple {i + 1}: {label}...", expanded=True):
            st.markdown(f"**Situation:** {triple['situation']}")
            st.markdown(f"**Action Taken:** {triple['action_taken']}")
            st.markdown(f"**Tactical Field Intent:** {triple.get('tactical_field_intent', triple.get('intent', ''))}")

            st.divider()
            score_default = saved.get("tactical_viability_score", 3)
            score = st.slider(
                "Tactical Viability Score (1 = Politically Reckless, 5 = Masterful Field Move)",
                min_value=1,
                max_value=5,
                value=int(score_default),
                key=f"f2_score_{i}",
            )
            f2_inputs.append({
                "triple_index": i,
                "tactical_viability_score": score,
            })

    # ── FORMAT 3: RL Scenario ────────────────────────────────────────────────
    st.header("Format 3: RL Scenario Evaluation")

    CATEGORY_OPTIONS = ["Passive", "Proactive", "Overstep"]
    f3_inputs = []

    for i, option in enumerate(rl_scenario):
        saved_f3 = f3_saved.get(i, {}) if isinstance(f3_saved, dict) else {}
        with st.expander(f"Action Option {i + 1}", expanded=True):
            st.markdown(f"**Description:** {option['description']}")

            st.divider()
            cat_default = 0
            if saved_f3.get("pn_category") in CATEGORY_OPTIONS:
                cat_default = CATEGORY_OPTIONS.index(saved_f3["pn_category"])
            pn_category = st.selectbox(
                "Categorize this action:",
                CATEGORY_OPTIONS,
                index=cat_default,
                key=f"f3_cat_{i}",
            )

            f3_inputs.append({
                "option_index": i,
                "pn_category": pn_category,
                "ai_intended_category": option.get("ai_intended_category", ""),
            })

    # ── FINAL ASSESSMENT ──────────────────────────────────────────────────────
    st.divider()
    st.header("Final Assessment: Overall Field Authenticity")
    st.markdown(
        "Rate the **Overall Field Authenticity** of this synthetic case. "
        "Did the systemic timeline bottlenecks (Format 1), the tactical field "
        "maneuvers (Format 2), and the political boundary dilemmas (Format 3) "
        "accurately reflect your lived experience in the field?"
    )

    # Load saved value from session if resuming
    session_resp = _retry(lambda: (
        client.table("evaluation_sessions")
        .select("overall_field_authenticity")
        .eq("id", session_id)
        .single()
        .execute()
    ))
    saved_authenticity = session_resp.data.get("overall_field_authenticity") or 3

    overall_score = st.slider(
        "1 = Completely Artificial / Textbook — 5 = Highly Authentic / Rings 100% True",
        min_value=1,
        max_value=5,
        value=int(saved_authenticity),
        key="overall_field_authenticity",
    )

    # ── AUTO-SAVE on every interaction ─────────────────────────────────────────
    _save_answers(client, session_id, f1_inputs, f2_inputs, f3_inputs,
                  case_label, navigator_name)
    client.table("evaluation_sessions").update({
        "overall_field_authenticity": overall_score,
    }).eq("id", session_id).execute()

    # ── SUBMIT ──────────────────────────────────────────────────────────────────
    st.divider()

    if st.button("Submit Evaluation", type="primary", use_container_width=True):
        _save_answers(client, session_id, f1_inputs, f2_inputs, f3_inputs,
                      case_label, navigator_name)

            # Mark session completed with overall score
            client.table("evaluation_sessions").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "overall_field_authenticity": overall_score,
            }).eq("id", session_id).execute()

            st.success("Evaluation submitted successfully!")
            st.session_state.pop("current_session_id", None)
            st.session_state.pop("current_case_id", None)
            st.session_state["current_page"] = "pn_dashboard"
            st.rerun()
