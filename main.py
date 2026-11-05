import streamlit as st
import asyncio
import json
from pyodide.http import pyfetch

SUPABASE_URL = "https://bfjiwafmysriugxmnmbr.supabase.co"
SUPABASE_KEY = "sb_publishable_cAFsSAfXjaeC_JSc0527Rw_I2sPNefR"


async def supabase_request(path, method="GET", body=None, access_token=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    response = await pyfetch(
        f"{SUPABASE_URL}{path}",
        method=method,
        headers=headers,
        body=json.dumps(body) if body is not None else None,
    )
    response_body = await response.string()
    return response.status, json.loads(response_body) if response_body else {}


def request_supabase(path, method="GET", body=None, access_token=None):
    return asyncio.run(supabase_request(path, method, body, access_token))

with st.form("signup_form"):
    email = st.text_input("Enter your email")
    password = st.text_input("Enter your password", type="password")
    displayName = st.text_input("Enter your display name")
    submitted = st.form_submit_button("Signup")
if submitted:
    if not email.strip() or not password:
        st.error("Enter an email and password.")
    else:
        try:
            status, data = request_supabase(
                "/auth/v1/signup",
                method="POST",
                body={
                    "email": email.strip(),
                    "password": password,
                    "data": {"displayName": displayName.strip()},
                },
            )
            if status >= 400:
                st.error(data.get("msg", data.get("message", "Signup failed.")))
            elif not data.get("session"):
                st.info("Account created. Check your email to confirm it.")
            else:
                st.success("Account created!")
        except Exception as e:
            st.error(f"Signup failed: {e}")
with st.form("login_form"):
    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input(
        "Password",
        type="password",
        key="login_password",
    )
    login_submitted = st.form_submit_button("Login")

if login_submitted:
    if not login_email.strip() or not login_password:
        st.error("Enter your email and password.")
    else:
        try:
            status, data = request_supabase(
                "/auth/v1/token?grant_type=password",
                method="POST",
                body={
                    "email": login_email.strip(),
                    "password": login_password,
                },
            )
            if status >= 400:
                st.error(data.get("error_description", data.get("msg", "Invalid email or password.")))
            else:
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data["refresh_token"]
                st.session_state["user"] = data["user"]

                message_status, messages = request_supabase(
                    "/rest/v1/messages?select=id,message",
                    access_token=data["access_token"],
                )
                if message_status >= 400:
                    st.error(messages.get("message", "Login succeeded, but messages could not be loaded."))
                else:
                    display_name = data["user"].get("user_metadata", {}).get("displayName", login_email)
                    st.success(f"Welcome back, {display_name}!")
                    st.write(messages)
        except Exception as e:
            st.error(f"Login failed: {e}")