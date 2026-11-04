import streamlit as st
import supabase
import httpx
supabaseClient = supabase.create_client(
    "https://bfjiwafmysriugxmnmbr.supabase.co",
    "sb_publishable_cAFsSAfXjaeC_JSc0527Rw_I2sPNefR"
)
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
            response = supabaseClient.auth.sign_up({
                "email": email.strip(),
                "password": password,
                "options": {
                    "data": {
                        "displayName": displayName.strip()
                    }
                }
            })

            if response.user is None:
                st.error("Signup did not return a user.")
            elif response.session is None:
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
            auth_response = httpx.post(
                "https://bfjiwafmysriugxmnmbr.supabase.co/auth/v1/token?grant_type=password",
                headers={
                    "apikey": "sb_publishable_cAFsSAfXjaeC_JSc0527Rw_I2sPNefR",
                    "Content-Type": "application/json",
                },
                json={
                    "email": login_email.strip(),
                    "password": login_password,
                },
            )

            data = auth_response.json()

            if auth_response.status_code != 200:
                st.error(data.get("error_description", "Invalid email or password."))
            else:
                st.session_state["access_token"] = data["access_token"]
                st.session_state["user"] = data["user"]
                st.success(f"Welcome back, {data['user']['user_metadata']['displayName']}!")

        except Exception as e:
            st.error(f"Login failed: {e}")