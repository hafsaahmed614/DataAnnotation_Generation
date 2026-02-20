"""
Authentication helpers: sign-up, sign-in, sign-out, and session state utilities.

Uses 4-digit PIN login. Supabase admin API creates users with email
auto-confirmed so no confirmation emails are ever sent. The user only
sees Full Name + PIN.
"""

import streamlit as st
from app.supabase_client import get_supabase_client, get_service_client


def _name_pin_to_email(full_name: str, pin: str) -> str:
    """Convert full name + PIN to a deterministic email for Supabase auth."""
    clean = full_name.strip().lower().replace(" ", ".")
    return f"{clean}.{pin}@annotationplatform.com"


def sign_up(full_name: str, pin: str) -> dict:
    """Register a new navigator with full name + 4-digit PIN."""
    service = get_service_client()
    email = _name_pin_to_email(full_name, pin)
    password = f"pin{pin}xx"
    try:
        # Admin API: creates user with email already confirmed, no email sent
        user_response = service.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        user = user_response.user
        if not user:
            return {"success": False, "error": "Sign-up failed. Please try a different PIN."}

        service.table("profiles").insert({
            "id": str(user.id),
            "role": "navigator",
            "full_name": full_name,
            "pin": pin,
        }).execute()

        return {"success": True}
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg.lower() or "already registered" in error_msg.lower():
            return {"success": False, "error": "That name + PIN combination is already registered."}
        return {"success": False, "error": error_msg}


def sign_in(full_name: str, pin: str) -> dict:
    """Sign in with full name + 4-digit PIN."""
    client = get_supabase_client()
    email = _name_pin_to_email(full_name, pin)
    password = f"pin{pin}xx"
    try:
        auth_response = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        user = auth_response.user
        session = auth_response.session

        if not user or not session:
            return {"success": False, "error": "Invalid name or PIN."}

        st.session_state["access_token"] = session.access_token
        st.session_state["refresh_token"] = session.refresh_token
        st.session_state["user_id"] = str(user.id)

        client.auth.set_session(session.access_token, session.refresh_token)

        profile = (
            get_service_client()
            .table("profiles")
            .select("role, full_name")
            .eq("id", str(user.id))
            .single()
            .execute()
        )
        st.session_state["role"] = profile.data["role"]
        st.session_state["full_name"] = profile.data["full_name"]
        st.session_state["authenticated"] = True

        return {"success": True, "role": profile.data["role"]}
    except Exception as e:
        return {"success": False, "error": "Invalid name or PIN. Please try again."}


def sign_out():
    """Clear session state and sign out from Supabase."""
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    for key in [
        "access_token", "refresh_token", "user_id", "role",
        "full_name", "authenticated", "current_page",
        "current_session_id", "current_case_id",
    ]:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def get_role() -> str:
    return st.session_state.get("role", "")


def get_user_id() -> str:
    return st.session_state.get("user_id", "")
