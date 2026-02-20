"""
Data Annotation Platform — Main Entrypoint

Sidebar navigation with role-based page visibility.

Usage:
    streamlit run streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Data Annotation Platform",
    layout="wide",
)

from app.auth import is_authenticated, get_role, sign_out
from app.pages import login, admin_dashboard, pn_dashboard, annotation


def render_sidebar():
    """Render sidebar navigation — all pages always visible."""
    with st.sidebar:
        st.title("Navigation")

        if is_authenticated():
            st.write(f"Signed in as **{st.session_state.get('full_name', '')}**")
            role_display = "Patient Navigator" if get_role() == "navigator" else get_role().title()
            st.write(f"Role: `{role_display}`")
            st.divider()

        if st.button("Sign In / Register", use_container_width=True):
            st.session_state["current_page"] = "login"
            st.rerun()

        if st.button("Admin Dashboard", use_container_width=True):
            st.session_state["current_page"] = "admin_dashboard"
            st.rerun()

        if st.button("My Cases", use_container_width=True):
            st.session_state["current_page"] = "pn_dashboard"
            st.rerun()

        if st.session_state.get("current_session_id"):
            if st.button("Current Evaluation", use_container_width=True):
                st.session_state["current_page"] = "annotation"
                st.rerun()

        if is_authenticated():
            st.divider()
            if st.button("Logout", use_container_width=True):
                sign_out()
                st.session_state["current_page"] = "login"
                st.rerun()


def _require_auth(role=None):
    """Show sign-in prompt if not authenticated or wrong role. Returns True if blocked."""
    if not is_authenticated():
        st.warning("Please sign in to access this page.")
        return True
    if role and get_role() != role:
        st.error(f"Access denied. {role.title()} role required.")
        return True
    return False


def main():
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "login"

    render_sidebar()

    page = st.session_state["current_page"]

    if page == "login":
        login.render()
    elif page == "admin_dashboard":
        admin_dashboard.render()
    elif page == "pn_dashboard":
        if not _require_auth("navigator"):
            pn_dashboard.render()
    elif page == "annotation":
        if not _require_auth("navigator"):
            annotation.render()
    else:
        login.render()


if __name__ == "__main__":
    main()
