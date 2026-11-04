import streamlit as st
import supabase
from st_login_form import login_form
supabaseClient = supabase.create_client(
    "https://bfjiwafmysriugxmnmbr.supabase.co",
    "sb_publishable_cAFsSAfXjaeC_JSc0527Rw_I2sPNefR"
)
email = st.text_input("Enter your email address", type="email")
password = st.text_input("Enter your password", type="password")
if st.button("Sign Up"):
    if not email.strip() or not password:
        st.error("Enter both your email and password.")
    else:
        credentials = {
            "email": email.strip(),
            "password": password
        }
if st.button("Login"):
    if not email.strip() or not password:
        st.error("Enter both your email and password.")
    else:
        credentials = {
            "email": email.strip(),
            "password": password
        }

        session_response = supabaseClient.auth.sign_in_with_password(credentials)
        