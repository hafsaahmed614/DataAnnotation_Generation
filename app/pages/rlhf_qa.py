"""
Page E: RLHF Q&A — Human Review of Qwen Taxonomy Auditor

Navigators review Qwen's auto-generated evaluations for Format 2 (tactical
triples) and Format 3 (RL scenarios), then submit Agree/Disagree feedback
plus optional corrections and notes. Feedback is persisted to Supabase
(f2_rlhf_feedback / f3_rlhf_feedback).

The question bank is loaded from static CSVs in data/rlhf/. Those CSVs are
read-only — all human input is written to Supabase.
"""

import os
import re
import pandas as pd
import streamlit as st

from app.supabase_client import get_authenticated_client
from app.auth import get_user_id


F2_CSV_PATH = os.path.join("data", "rlhf", "f2_RLHF_backend.csv")
F3_CSV_PATH = os.path.join("data", "rlhf", "f3_RLHF_backend.csv")

CATEGORY_OPTIONS = ["Passive", "Proactive", "Overstep"]


def _batch_display_name(batch_id: str) -> str:
    """Convert a batch_id like 'synthetic_batch_25_v11' or 'synthetic_batch_25' into 'Batch 11' / 'Batch 1'."""
    if not batch_id:
        return "Batch ?"
    m = re.search(r"_v(\d+)$", batch_id)
    if m:
        return f"Batch {m.group(1)}"
    # Base table with no version suffix is v1
    return "Batch 1"


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def _load_csvs():
    """Load both RLHF backend CSVs into DataFrames. Cached across reruns."""
    f2 = pd.read_csv(F2_CSV_PATH)
    f3 = pd.read_csv(F3_CSV_PATH)
    return f2, f3


def _build_case_index(f2_df: pd.DataFrame, f3_df: pd.DataFrame):
    """Return a sorted list of (case_id, batch_id, case_label, narrative_summary)
    tuples representing every unique case across both CSVs."""
    cols = ["case_id", "batch_id", "case_label", "narrative_summary"]
    combined = pd.concat([f2_df[cols], f3_df[cols]], ignore_index=True)
    unique = combined.drop_duplicates(subset=["case_id"]).reset_index(drop=True)

    def sort_key(row):
        batch_id = str(row.get("batch_id", ""))
        bm = re.search(r"_v(\d+)$", batch_id)
        batch_num = int(bm.group(1)) if bm else 1
        cm = re.search(r"(\d+)", str(row.get("case_label", "")))
        case_num = int(cm.group(1)) if cm else 0
        return (batch_num, case_num)

    unique["__sort"] = unique.apply(sort_key, axis=1)
    unique = unique.sort_values("__sort").drop(columns="__sort").reset_index(drop=True)
    return unique


def _fetch_existing_feedback(client, navigator_id: str, case_id: str):
    """Fetch any previously saved RLHF feedback rows for this navigator + case.

    Returns two dicts keyed by question/scenario index.
    """
    f2_resp = (
        client.table("f2_rlhf_feedback")
        .select("*")
        .eq("navigator_id", navigator_id)
        .eq("case_id", case_id)
        .execute()
    )
    f3_resp = (
        client.table("f3_rlhf_feedback")
        .select("*")
        .eq("navigator_id", navigator_id)
        .eq("case_id", case_id)
        .execute()
    )
    f2_by_idx = {row["f2_question_index"]: row for row in (f2_resp.data or [])}
    f3_by_idx = {row["f3_scenario_index"]: row for row in (f3_resp.data or [])}
    return f2_by_idx, f3_by_idx


def _fetch_navigator_progress(client, navigator_id: str):
    """Fetch all of a navigator's saved RLHF rows in two queries.

    Returns two dicts: {case_id: count_of_saved_rows} for F2 and F3.
    """
    f2_counts = {}
    f3_counts = {}

    f2_resp = (
        client.table("f2_rlhf_feedback")
        .select("case_id")
        .eq("navigator_id", navigator_id)
        .execute()
    )
    for row in (f2_resp.data or []):
        cid = row.get("case_id")
        f2_counts[cid] = f2_counts.get(cid, 0) + 1

    f3_resp = (
        client.table("f3_rlhf_feedback")
        .select("case_id")
        .eq("navigator_id", navigator_id)
        .execute()
    )
    for row in (f3_resp.data or []):
        cid = row.get("case_id")
        f3_counts[cid] = f3_counts.get(cid, 0) + 1

    return f2_counts, f3_counts


def _compute_expected_counts(f2_df: pd.DataFrame, f3_df: pd.DataFrame):
    """Return two dicts: {case_id: total_questions} for F2 and F3 from the CSVs."""
    f2_expected = f2_df.groupby("case_id").size().to_dict()
    f3_expected = f3_df.groupby("case_id").size().to_dict()
    return f2_expected, f3_expected


def _progress_symbol(case_id, f2_saved, f3_saved, f2_expected, f3_expected) -> str:
    """Return ✅ if fully complete, ⏳ if partially complete, '' otherwise."""
    saved = f2_saved.get(case_id, 0) + f3_saved.get(case_id, 0)
    if saved == 0:
        return ""
    expected = f2_expected.get(case_id, 0) + f3_expected.get(case_id, 0)
    if saved >= expected and expected > 0:
        return "✅ "
    return "⏳ "


# ── Save logic ───────────────────────────────────────────────────────────────

def _save_feedback(client, navigator_id, navigator_name, case_row, f2_inputs, f3_inputs):
    """Upsert all collected F2 + F3 feedback rows to Supabase."""
    case_id = case_row["case_id"]
    batch_id = case_row.get("batch_id", "")
    case_label = case_row.get("case_label", "")

    f2_rows = []
    for idx, inp in f2_inputs.items():
        if inp.get("human_agree_score") is None:
            continue  # skip rows the navigator hasn't touched
        f2_rows.append({
            "navigator_id": navigator_id,
            "navigator_name": navigator_name,
            "case_id": case_id,
            "batch_id": batch_id,
            "case_label": case_label,
            "f2_question_index": int(idx),
            "human_agree_score": inp.get("human_agree_score"),
            "human_agree_or_disagree_rationale": inp.get("human_agree_or_disagree_rationale") or None,
            "human_corrected_score": inp.get("human_corrected_score"),
            "updated_at": "now()",
        })

    f3_rows = []
    for idx, inp in f3_inputs.items():
        if inp.get("human_agree_category") is None:
            continue
        f3_rows.append({
            "navigator_id": navigator_id,
            "navigator_name": navigator_name,
            "case_id": case_id,
            "batch_id": batch_id,
            "case_label": case_label,
            "f3_scenario_index": int(idx),
            "human_agree_category": inp.get("human_agree_category"),
            "human_agree_or_disagree_rationale": inp.get("human_agree_or_disagree_rationale") or None,
            "human_corrected_category": inp.get("human_corrected_category"),
            "updated_at": "now()",
        })

    if f2_rows:
        client.table("f2_rlhf_feedback").upsert(
            f2_rows,
            on_conflict="navigator_id,case_id,f2_question_index",
        ).execute()
    if f3_rows:
        client.table("f3_rlhf_feedback").upsert(
            f3_rows,
            on_conflict="navigator_id,case_id,f3_scenario_index",
        ).execute()

    return len(f2_rows), len(f3_rows)


# ── UI rendering ─────────────────────────────────────────────────────────────

def _render_f2_section(f2_rows: pd.DataFrame, prefilled: dict, case_id: str):
    """Render expanders for each F2 tactical triple. Collect inputs in session state."""
    st.header("Format 2: Tactical Reasoning Triples")

    if len(f2_rows) == 0:
        st.info("No Format 2 questions for this case.")
        return {}

    inputs = {}
    for _, row in f2_rows.iterrows():
        idx = int(row["f2_question_index"])
        prior = prefilled.get(idx, {})

        with st.expander(f"Tactic {idx}", expanded=False):
            st.markdown(f"**Situation:** {row['situation']}")
            st.markdown(f"**Action Taken:** {row['action_taken']}")
            st.markdown(f"**Intent:** {row['intent']}")

            st.divider()
            st.markdown("**Qwen Score (1–5):**")
            try:
                qwen_score = int(row["qwen_score"])
            except (ValueError, TypeError):
                qwen_score = 0
            st.progress(qwen_score / 5 if qwen_score else 0, text=f"Score: {qwen_score}/5")
            st.markdown(f"**Qwen Rationale:** {row['qwen_rationale']}")

            st.divider()

            # Default to prior saved value if any
            agree_default = prior.get("human_agree_score")
            agree_idx = (["Agree", "Disagree"].index(agree_default)
                         if agree_default in ["Agree", "Disagree"] else None)

            agree = st.radio(
                "Do you agree with Qwen's score?",
                options=["Agree", "Disagree"],
                index=agree_idx,
                key=f"f2_agree_{case_id}_{idx}",
                horizontal=True,
            )

            rationale = st.text_area(
                "Which parts of Qwen's rationale do you agree or disagree with? Feel free to share your own reasoning.",
                value=prior.get("human_agree_or_disagree_rationale") or "",
                key=f"f2_rationale_{case_id}_{idx}",
                height=120,
            )

            corrected_score = None
            if agree == "Disagree":
                default_corrected = prior.get("human_corrected_score") or qwen_score or 3
                corrected_score = st.slider(
                    "Your corrected score (1–5):",
                    min_value=1, max_value=5,
                    value=int(default_corrected),
                    key=f"f2_corrected_{case_id}_{idx}",
                )

            inputs[idx] = {
                "human_agree_score": agree,
                "human_agree_or_disagree_rationale": rationale,
                "human_corrected_score": corrected_score,
            }

    return inputs


def _render_f3_section(f3_rows: pd.DataFrame, prefilled: dict, case_id: str):
    """Render expanders for each F3 RL scenario. Collect inputs in session state."""
    st.header("Format 3: RL Boundary Scenarios")

    if len(f3_rows) == 0:
        st.info("No Format 3 scenarios for this case.")
        return {}

    inputs = {}
    for _, row in f3_rows.iterrows():
        idx = int(row["f3_scenario_index"])
        prior = prefilled.get(idx, {})

        with st.expander(f"Scenario {idx}", expanded=False):
            st.markdown(f"**Description:** {row['description']}")

            st.divider()
            st.markdown(f"**Qwen Category:** `{row['qwen_category']}`")
            st.markdown(f"**Qwen Rationale:** {row['qwen_rationale']}")

            st.divider()

            agree_default = prior.get("human_agree_category")
            agree_idx = (["Agree", "Disagree"].index(agree_default)
                         if agree_default in ["Agree", "Disagree"] else None)

            agree = st.radio(
                "Do you agree with Qwen's category?",
                options=["Agree", "Disagree"],
                index=agree_idx,
                key=f"f3_agree_{case_id}_{idx}",
                horizontal=True,
            )

            rationale = st.text_area(
                "Which parts of Qwen's rationale do you agree or disagree with? Feel free to share your own reasoning.",
                value=prior.get("human_agree_or_disagree_rationale") or "",
                key=f"f3_rationale_{case_id}_{idx}",
                height=120,
            )

            corrected_category = None
            if agree == "Disagree":
                qwen_cat = row.get("qwen_category", "Passive")
                default_corrected = prior.get("human_corrected_category") or qwen_cat
                cat_idx = (CATEGORY_OPTIONS.index(default_corrected)
                           if default_corrected in CATEGORY_OPTIONS else 0)
                corrected_category = st.selectbox(
                    "Your corrected category:",
                    options=CATEGORY_OPTIONS,
                    index=cat_idx,
                    key=f"f3_corrected_{case_id}_{idx}",
                )

            inputs[idx] = {
                "human_agree_category": agree,
                "human_agree_or_disagree_rationale": rationale,
                "human_corrected_category": corrected_category,
            }

    return inputs


# ── Main render ──────────────────────────────────────────────────────────────

def render():
    client = get_authenticated_client()
    user_id = get_user_id()
    navigator_name = st.session_state.get("full_name", "Navigator")

    st.title("RLHF — Qwen Auditor Review")
    st.caption("Review Qwen's automated scoring of Format 2 and Format 3 outputs and provide your feedback.")

    # Load CSVs
    try:
        f2_df, f3_df = _load_csvs()
    except FileNotFoundError as e:
        st.error(f"RLHF backend CSV not found: {e}")
        return

    case_index = _build_case_index(f2_df, f3_df)
    if len(case_index) == 0:
        st.warning("No cases found in the RLHF backend CSVs.")
        return

    # Initialize current case index in session state
    if "rlhf_case_idx" not in st.session_state:
        st.session_state["rlhf_case_idx"] = 0

    # ── Compute progress for this navigator ──────────────────────────────────
    f2_saved_counts, f3_saved_counts = _fetch_navigator_progress(client, user_id)
    f2_expected_counts, f3_expected_counts = _compute_expected_counts(f2_df, f3_df)

    # ── Sidebar case selector ────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("RLHF Case Selector")

        st.markdown(
            "**Legend**  \n"
            "✅ &nbsp; Completed  \n"
            "⏳ &nbsp; In Progress"
        )

        case_labels = [
            f"{_progress_symbol(row['case_id'], f2_saved_counts, f3_saved_counts, f2_expected_counts, f3_expected_counts)}"
            f"{_batch_display_name(row['batch_id'])} — {row['case_label']}"
            for _, row in case_index.iterrows()
        ]
        selected_label = st.selectbox(
            "Select a case:",
            options=case_labels,
            index=st.session_state["rlhf_case_idx"],
            key="rlhf_case_selector",
        )
        selected_idx = case_labels.index(selected_label)
        if selected_idx != st.session_state["rlhf_case_idx"]:
            st.session_state["rlhf_case_idx"] = selected_idx
            st.rerun()

        st.caption(f"Case {selected_idx + 1} of {len(case_index)}")

    case_row = case_index.iloc[st.session_state["rlhf_case_idx"]].to_dict()
    case_id = case_row["case_id"]

    # ── Global case context ──────────────────────────────────────────────────
    st.header(f"{case_row['case_label']}  ·  {_batch_display_name(case_row['batch_id'])}")
    with st.container(border=True):
        st.markdown("**Narrative Summary**")
        st.write(case_row.get("narrative_summary", ""))

    # ── Pull existing feedback for prefill ───────────────────────────────────
    f2_prior, f3_prior = _fetch_existing_feedback(client, user_id, case_id)

    # ── Filter rows for this case ────────────────────────────────────────────
    f2_rows = (
        f2_df[f2_df["case_id"] == case_id]
        .sort_values("f2_question_index")
        .reset_index(drop=True)
    )
    f3_rows = (
        f3_df[f3_df["case_id"] == case_id]
        .sort_values("f3_scenario_index")
        .reset_index(drop=True)
    )

    f2_inputs = _render_f2_section(f2_rows, f2_prior, case_id)
    f3_inputs = _render_f3_section(f3_rows, f3_prior, case_id)

    # ── Save ─────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("Save Annotations", use_container_width=True, type="primary"):
        try:
            n_f2, n_f3 = _save_feedback(
                client, user_id, navigator_name, case_row, f2_inputs, f3_inputs
            )
            st.success(f"Saved {n_f2} F2 + {n_f3} F3 annotations.")
            st.rerun()
        except Exception as e:
            st.error(f"Save failed: {e}")
