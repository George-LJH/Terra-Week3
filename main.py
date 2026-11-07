import streamlit as st
import asyncio
import json
from streamlit_autorefresh import st_autorefresh
from pyodide.http import pyfetch
from datetime import datetime
st.markdown(
    """
    <style>
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Constrain chat message area */
    [data-testid="stChatMessageContainer"] {
        max-height: 70vh;
        overflow-y: auto;
        padding-right: 8px;
    }
    .css-1y0tads {padding-top: 0rem;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp [data-testid="stToolbar"]{
    display:none;
    }
    </style>
    """,
    unsafe_allow_html=True,
    )
if "screen" not in st.session_state:
    st.session_state["screen"] = "homepage"
if "target" not in st.session_state:
    st.session_state["target"] = None

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


def writeMessage(message, current_user_id, target_user_id, access_token):
    status, data = request_supabase(
        "/rest/v1/messages",
        method="POST",
        body={
            "message": message,
            "from": current_user_id,
            "to": [target_user_id],
            "accesableBy": [current_user_id, target_user_id],
        },
        access_token=access_token,
    )
    if status >= 400:
        raise RuntimeError(data.get("message", "Could not send message."))


def readMessages(access_token, current_user_id, target_user_id):
    status, messages = request_supabase(
        '/rest/v1/messages?select=id,message,"from","to",created_at&order=id.asc',
        access_token=access_token,
    )
    if status >= 400:
        raise RuntimeError(messages.get("message", "Could not read messages."))

    return [
        message
        for message in messages
        if (
            message.get("from") in {current_user_id, target_user_id}
            and target_user_id in message.get("to", [])
        )
        or (
            message.get("from") == target_user_id
            and current_user_id in message.get("to", [])
        )
    ]


def getUserID(access_token):
    status, user_data = request_supabase(
        "/auth/v1/user",
        access_token=access_token,
    )
    if status >= 400:
        raise RuntimeError(user_data.get("message", "Could not get user ID."))
    return user_data["id"]


def request_supabase(path, method="GET", body=None, access_token=None):
    return asyncio.run(supabase_request(path, method, body, access_token))


def signup():
    with st.form("signup_form"):
        email = st.text_input("Enter your email")
        password = st.text_input("Enter your password", type="password")
        display_name = st.text_input("Enter your display name")
        submitted = st.form_submit_button("Signup")

    if not submitted:
        return

    email = email.strip()
    display_name = display_name.strip()

    if not email or not password or not display_name:
        st.error("Enter your email, password, and display name.")
        return

    try:
        status, data = request_supabase(
            "/auth/v1/signup",
            method="POST",
            body={
                "email": email,
                "password": password,
                "data": {"displayName": display_name},
            },
        )

        if not isinstance(data, dict):
            data = {}

        if status >= 400:
            error = (
                data.get("msg")
                or data.get("message")
                or data.get("error_description")
                or data.get("error")
                or "Signup failed."
            )
            st.error(str(error))
            return

        session = data.get("session")
        access_token = data.get("access_token")

        if not access_token and isinstance(session, dict):
            access_token = session.get("access_token")

        if access_token:
            user = data.get("user")
            if not user and isinstance(session, dict):
                user = session.get("user")

            if not user:
                user_status, user = request_supabase(
                    "/auth/v1/user",
                    access_token=access_token,
                )
                if user_status >= 400:
                    raise RuntimeError(user.get("message", "Could not load the new user."))

            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = data.get("refresh_token") or session.get("refresh_token")
            st.session_state["user"] = user
            st.success("Account created and signed in!")
            st.session_state["screen"] = "searchUser"
            st.rerun()
        else:
            st.info("Account created. Check your email to confirm it.")

    except Exception as e:
        st.error(f"Signup failed: {e}")


def login():
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

                    display_name = data["user"].get("user_metadata", {}).get("displayName", login_email)
                    st.session_state["screen"] = "searchUser"
                    st.session_state["target"] = None
                    st.success(f"Welcome back, {display_name}!")
                    st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

def message_list():
    target = st.session_state["target"]
    current_user_id = st.session_state["user"]["id"]
    st.caption(f"Fragment refreshed: {datetime.now().strftime('%H:%M:%S')}")
    try:
        messages = readMessages(
            st.session_state["access_token"],
            current_user_id,
            target["id"],
        )
        for db_message in messages:
            is_current_user = db_message["from"] == current_user_id
            with st.chat_message("user" if is_current_user else "assistant"):
                st.write(db_message["message"])
    except Exception as exc:
        st.error(str(exc))

if st.session_state["screen"] == "homepage":
    st.title("Welcome to the Streamlit Supabase App")
    st.write("Please sign up or log in to continue.")

    col1, col2 = st.columns(2)
    with col1:
        st.header("Sign Up")
        signup()

    with col2:
        st.header("Log In")
        login()

elif st.session_state["screen"] == "searchUser":
    st.title("Search User")
    st.write("You are now logged in. You can search for users here.")
    st.subheader("Contacts")

    try:
        status, contacts = request_supabase(
            "/rest/v1/profiles?select=id,displayName&order=displayName",
            access_token=st.session_state["access_token"],
        )

        if status >= 400:
            st.error(contacts.get("message", "Could not load contacts."))
        elif not contacts:
            st.info("No profiles found.")
        else:
            options = {
                contact.get("displayName") or "Unnamed user": contact
                for contact in contacts
                if contact["id"] != st.session_state["user"]["id"]
            }
            target_name = st.selectbox(
                "select a user:",
                list(options),
                index=None,
                placeholder="search User...",
            )
            if target_name:
                st.session_state["screen"] = "chat"
                st.session_state["target"] = options[target_name]
                st.rerun()
    except Exception as exc:
        st.error(f"Could not load contacts: {exc}")

elif st.session_state["screen"] == "chat":
    st_autorefresh(interval=2000, key="msg_poll")
    
    target = st.session_state["target"]
    current_user_id = st.session_state["user"]["id"]
    st.title(f"Chat with {target['displayName'] or 'Unnamed user'}")

    messages = readMessages(st.session_state["access_token"], current_user_id, target["id"])
    
    # Fetch all profiles to map user IDs to display names
    status, profiles = request_supabase(
        "/rest/v1/profiles?select=id,displayName",
        access_token=st.session_state["access_token"],
    )
    name_map = {p["id"]: p.get("displayName") or "Unknown" for p in profiles} if status < 400 else {}
    # Add current user's name from session
    name_map[current_user_id] = st.session_state["user"].get("user_metadata", {}).get("displayName", "You")
    
    for msg in messages:
        sender_name = name_map.get(msg["from"], "Unknown")
        is_current_user = msg["from"] == current_user_id
        dt = datetime.fromisoformat(msg["created_at"])
        timeStr = dt.astimezone().strftime("%Y-%m-%d %I:%M:%S %p")
        # timeStr = dt.strftime("%Y-%m-%d %H:%M:%S")
        with st.chat_message("user" if is_current_user else "assistant"):

            st.markdown(f"**{sender_name}**")
            st.write(msg["message"])
            st.caption(f"Sent at: {timeStr}")
    message = st.chat_input("Say something", accept_file = False)
    st.markdown(
        """
        <script>
        setTimeout(() => {
            const container = document.querySelector('[data-testid="stChatMessageContainer"]');
            if (container) container.scrollTop = container.scrollHeight;
        }, 0);
        </script>
        """,
        unsafe_allow_html=True,
    )
    if message and message.strip():
        writeMessage(message.strip(), current_user_id, target["id"], st.session_state["access_token"])
        st.rerun()
