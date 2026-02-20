"""
Page B: Admin Dashboard

Shows navigator progress (completed/in-progress/remaining per PN)
and a data table of all loaded synthetic cases.
"""

import streamlit as st
import pandas as pd
from app.supabase_client import get_service_client


ADMIN_PASSWORD = "DataGeneration"


def render():
    st.title("Admin Dashboard")

    if not st.session_state.get("admin_unlocked"):
        with st.form("admin_password_form"):
            password = st.text_input("Enter admin password", type="password")
            submitted = st.form_submit_button("Unlock")
            if submitted:
                if password == ADMIN_PASSWORD:
                    st.session_state["admin_unlocked"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        return

    client = get_service_client()

    # ── Navigator Progress ───────────────────────────────────────────────────
    st.header("Navigator Progress")

    navigators = (
        client.table("profiles")
        .select("id, full_name")
        .eq("role", "navigator")
        .execute()
    )
    sessions = (
        client.table("evaluation_sessions")
        .select("navigator_id, status")
        .execute()
    )
    total_cases_resp = (
        client.table("synthetic_cases")
        .select("id", count="exact")
        .execute()
    )
    total_cases = total_cases_resp.count or 0

    progress_data = []
    session_list = sessions.data or []
    for nav in navigators.data or []:
        nav_sessions = [s for s in session_list if s["navigator_id"] == nav["id"]]
        completed = sum(1 for s in nav_sessions if s["status"] == "completed")
        in_progress = sum(1 for s in nav_sessions if s["status"] == "in_progress")
        remaining = total_cases - completed - in_progress
        progress_data.append({
            "Navigator": nav["full_name"],
            "Completed": completed,
            "In Progress": in_progress,
            "Remaining": remaining,
            "Progress": f"{completed}/{total_cases}",
        })

    if progress_data:
        st.dataframe(pd.DataFrame(progress_data), use_container_width=True, hide_index=True)
    else:
        st.info("No navigators registered yet.")

    # ── Synthetic Cases Table ────────────────────────────────────────────────
    st.header("Synthetic Cases")

    cases = (
        client.table("synthetic_cases")
        .select("label, batch_id, narrative_summary, created_at")
        .order("label")
        .execute()
    )

    if cases.data:
        df = pd.DataFrame(cases.data)
        df["narrative_summary"] = df["narrative_summary"].str[:120] + "..."
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No synthetic cases loaded. Run upload_cases.py first.")
