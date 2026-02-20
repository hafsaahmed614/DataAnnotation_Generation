"""
Supabase client initialization with session restoration.

Uses @st.cache_resource for a singleton client. Auth tokens are stored
in st.session_state and restored on each rerun via get_authenticated_client().
"""

import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def _get_secret(name: str) -> str:
    """Read from os.environ first, then fall back to st.secrets (Streamlit Cloud)."""
    val = os.environ.get(name)
    if val:
        return val
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        raise KeyError(f"Missing secret: {name}. Set it in .env or Streamlit Cloud Secrets.")


@st.cache_resource
def _init_client() -> Client:
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    return create_client(url, key)


def get_supabase_client() -> Client:
    """Return the base Supabase client (no auth session attached)."""
    return _init_client()


def get_authenticated_client() -> Client:
    """Return a Supabase client with the current user's session restored."""
    client = _init_client()
    if "access_token" in st.session_state and "refresh_token" in st.session_state:
        client.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"],
        )
    return client


@st.cache_resource
def get_service_client() -> Client:
    """Return a Supabase client using the service role key (bypasses RLS)."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)
