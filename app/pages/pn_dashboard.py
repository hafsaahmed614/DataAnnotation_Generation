"""
Page C: Patient Navigator Dashboard

Shows In-Progress (Resume), Pending (Start), and Completed evaluations.
"""

import re
import streamlit as st
from app.supabase_client import get_authenticated_client
from app.auth import get_user_id


def _label_sort_key(label: str) -> int:
    """Extract numeric part from label like 'Case_12' for proper ordering."""
    m = re.search(r"(\d+)", label or "")
    return int(m.group(1)) if m else 0


def render():
    client = get_authenticated_client()
    user_id = get_user_id()
    navigator_name = st.session_state.get("full_name", "Navigator")

    st.title("Navigator Dashboard")
    st.write(f"Welcome, {navigator_name}")

    # Fetch all cases and this navigator's sessions
    all_cases = (
        client.table("synthetic_cases")
        .select("id, label, narrative_summary")
        .execute()
    )
    my_sessions = (
        client.table("evaluation_sessions")
        .select("id, case_id, case_label, status, created_at, completed_at")
        .eq("navigator_id", user_id)
        .execute()
    )

    all_cases_sorted = sorted(all_cases.data or [], key=lambda c: _label_sort_key(c.get("label", "")))
    cases_dict = {c["id"]: c for c in all_cases_sorted}
    sessions_by_case = {s["case_id"]: s for s in (my_sessions.data or [])}

    pending_case_ids = [c["id"] for c in all_cases_sorted if c["id"] not in sessions_by_case]
    in_progress = sorted(
        [s for s in (my_sessions.data or []) if s["status"] == "in_progress"],
        key=lambda s: _label_sort_key(s.get("case_label", "")),
    )
    completed = sorted(
        [s for s in (my_sessions.data or []) if s["status"] == "completed"],
        key=lambda s: _label_sort_key(s.get("case_label", "")),
    )

    # ── In-Progress ──────────────────────────────────────────────────────────
    st.header(f"In Progress ({len(in_progress)})")
    if in_progress:
        for sess in in_progress:
            case = cases_dict.get(sess["case_id"], {})
            label = sess.get("case_label") or case.get("label", "")
            summary = (case.get("narrative_summary", "")[:120] + "...") if case else "Unknown case"
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"**{label}:** {summary}")
            with col_b:
                if st.button("Resume", key=f"resume_{sess['id']}"):
                    st.session_state["current_session_id"] = sess["id"]
                    st.session_state["current_case_id"] = sess["case_id"]
                    st.session_state["current_page"] = "annotation"
                    st.rerun()
    else:
        st.info("No evaluations in progress.")

    # ── Pending Cases ────────────────────────────────────────────────────────
    st.header(f"Pending Cases ({len(pending_case_ids)})")
    if pending_case_ids:
        for case_id in pending_case_ids:
            case = cases_dict[case_id]
            label = case.get("label", "")
            summary = (case.get("narrative_summary", "")[:120] + "...")
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"**{label}:** {summary}")
            with col_b:
                if st.button("Start", key=f"start_{case_id}"):
                    new_session = (
                        client.table("evaluation_sessions")
                        .insert({
                            "case_id": case_id,
                            "case_label": label,
                            "navigator_id": user_id,
                            "navigator_name": navigator_name,
                            "status": "in_progress",
                        })
                        .execute()
                    )
                    st.session_state["current_session_id"] = new_session.data[0]["id"]
                    st.session_state["current_case_id"] = case_id
                    st.session_state["current_page"] = "annotation"
                    st.rerun()
    else:
        st.info("All cases have been started or completed.")

    # ── Completed ────────────────────────────────────────────────────────────
    st.header(f"Completed ({len(completed)})")
    if completed:
        for sess in completed:
            case = cases_dict.get(sess["case_id"], {})
            label = sess.get("case_label") or case.get("label", "")
            summary = (case.get("narrative_summary", "")[:120] + "...") if case else "Unknown case"
            st.write(f"**{label}** — Completed {sess.get('completed_at', 'N/A')}: {summary}")
    else:
        st.info("No completed evaluations yet.")
