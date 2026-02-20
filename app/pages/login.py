"""
Page A: Login & Registration

4-digit PIN login. Register with name + PIN, sign in with name + PIN.
All registrations are navigators. Supabase email is auto-generated.
"""

import streamlit as st
from app.auth import sign_in, sign_up, is_authenticated


def render():
    st.title("Data Annotation Platform")
    st.subheader("Patient Navigator Case Evaluation System")

    if is_authenticated():
        name = st.session_state.get("full_name", "Navigator")
        st.success(f'Logged in as {name}. Please proceed to "My Cases" page.')
        return

    tab_register, tab_login = st.tabs(["Register", "Sign In"])

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Full Name")
            pin_reg = st.text_input("Create a 4-Digit PIN", max_chars=4, type="password")
            submitted_reg = st.form_submit_button("Register")

            if submitted_reg:
                if not full_name or not pin_reg:
                    st.error("Please fill in all fields.")
                elif len(pin_reg) != 4 or not pin_reg.isdigit():
                    st.error("PIN must be exactly 4 digits.")
                else:
                    result = sign_up(full_name, pin_reg)
                    if result["success"]:
                        st.success("Registration successful! Sign in with your name and PIN.")
                    else:
                        st.error(result["error"])

    with tab_login:
        with st.form("login_form"):
            full_name_login = st.text_input("Full Name")
            pin = st.text_input("4-Digit PIN", max_chars=4, type="password")
            submitted = st.form_submit_button("Sign In")

            if submitted:
                if not full_name_login:
                    st.error("Please enter your full name.")
                elif not pin or len(pin) != 4 or not pin.isdigit():
                    st.error("Please enter a valid 4-digit PIN.")
                else:
                    result = sign_in(full_name_login, pin)
                    if result["success"]:
                        st.rerun()
                    else:
                        st.error(result["error"])
