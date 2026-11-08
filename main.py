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
    /* Constrain chat message area */
    [data-testid="stChatMessageContainer"] {
        max-height: 70vh;
        overflow-y: auto;
        padding-right: 8px;
    }
    }
    </style>
    """,
    unsafe_allow_html=True,
    )
if "screen" not in st.session_state:
    st.session_state["screen"] = "homepage"
if "target" not in st.session_state:
    st.session_state["target"] = None

supabaseUrl = "https://bfjiwafmysriugxmnmbr.supabase.co"
supabaseKey = "sb_publishable_cAFsSAfXjaeC_JSc0527Rw_I2sPNefR"
async def createSignedUrl(accessToken, bucket, filePath, expiresIn=3600):
    url = f"{supabaseUrl}/storage/v1/object/sign/{bucket}/{filePath}"

    headers = {
        "apikey": supabaseKey,
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json",
    }

    response = await pyfetch(
        url,
        method="POST",
        headers=headers,
        body=json.dumps({"expiresIn": expiresIn}),
    )

    data = await response.json()

    if response.status >= 400:
        raise RuntimeError(data)

    signedPath = data["signedURL"]

    if signedPath.startswith("http"):
        return signedPath

    return f"{supabaseUrl}/storage/v1{signedPath}"
async def supabaseRequest(path, method="GET", body=None, accessToken=None):
    headers = {
        "apikey": supabaseKey,
        "Content-Type": "application/json",
    }
    if accessToken:
        headers["Authorization"] = f"Bearer {accessToken}"

    response = await pyfetch(
        f"{supabaseUrl}{path}",
        method=method,
        headers=headers,
        body=json.dumps(body) if body is not None else None,
    )
    responseBody = await response.string()
    return response.status, json.loads(responseBody) if responseBody else {}
async def uploadFile(accessToken, bucket, filePath, fileBytes, contentType):
    url = f"{supabaseUrl}/storage/v1/object/{bucket}/{filePath}"
    headers = {
        "apikey": supabaseKey,
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": contentType,
        "x-upsert": "true",
    }
    response = await pyfetch(url, method = "POST", headers=headers, body=fileBytes)
    responseBody = await response.string()
    return response.status, json.loads(responseBody) if responseBody else {}
def writeMessage(message, currentUserId, targetUserId, accessToken, fileInfos=None):
    body = {
        "message": message,
        "from": currentUserId,
        "to": [targetUserId],
        "accesableBy": [currentUserId, targetUserId],
    }
    if fileInfos:
        body["files"] = fileInfos   # Store as JSON array
    
    status, data = requestSupabase(
        "/rest/v1/messages",
        method="POST",
        body=body,
        accessToken=accessToken,
    )
    if status >= 400:
        raise RuntimeError(data.get("message", "Could not send message."))
def readMessages(accessToken, currentUserId, targetUserId):
    status, messages = requestSupabase(
        '/rest/v1/messages?select=id,message,"from","to",created_at,files&order=id.asc',
        accessToken=accessToken,
    )
    if status >= 400:
        raise RuntimeError(messages.get("message", "Could not read messages."))

    return [
        message
        for message in messages
        if (
            message.get("from") in {currentUserId, targetUserId}
            and targetUserId in message.get("to", [])
        )
        or (
            message.get("from") == targetUserId
            and currentUserId in message.get("to", [])
        )
    ]




def requestSupabase(path, method="GET", body=None, accessToken=None):
    return asyncio.run(supabaseRequest(path, method, body, accessToken))


def signup():
    with st.form("signup_form"):
        email = st.text_input("Enter your email")
        password = st.text_input("Enter your password", type="password")
        displayName = st.text_input("Enter your display name")
        submitted = st.form_submit_button("Signup")

    if not submitted:
        return

    email = email.strip()
    displayName = displayName.strip()

    if not email or not password or not displayName:
        st.error("Enter your email, password, and display name.")
        return

    try:
        status, data = requestSupabase(
            "/auth/v1/signup",
            method="POST",
            body={
                "email": email,
                "password": password,
                "data": {"displayName": displayName},
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
        accessToken = data.get("access_token")

        if not accessToken and isinstance(session, dict):
            accessToken = session.get("access_token")

        if accessToken:
            user = data.get("user")
            if not user and isinstance(session, dict):
                user = session.get("user")

            if not user:
                userStatus, user = requestSupabase(
                    "/auth/v1/user",
                    accessToken=accessToken,
                )
                if userStatus >= 400:
                    raise RuntimeError(user.get("message", "Could not load the new user."))

            st.session_state["access_token"] = accessToken
            # st.session_state["refresh_token"] = data.get("refresh_token") or session.get("refresh_token")
            session = data.get("session") or {}
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
        loginEmail = st.text_input("Email", key="login_email")
        loginPassword = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )
        loginSubmitted = st.form_submit_button("Login")

    if loginSubmitted:
        if not loginEmail.strip() or not loginPassword:
            st.error("Enter your email and password.")
        else:
            try:
                status, data = requestSupabase(
                    "/auth/v1/token?grant_type=password",
                    method="POST",
                    body={
                        "email": loginEmail.strip(),
                        "password": loginPassword,
                    },
                )
                if status >= 400:
                    st.error(data.get("error_description", data.get("msg", "Invalid email or password.")))
                else:
                    st.session_state["access_token"] = data["access_token"]
                    st.session_state["refresh_token"] = data["refresh_token"]
                    st.session_state["user"] = data["user"]

                    displayName = data["user"].get("user_metadata", {}).get("displayName", loginEmail)
                    st.session_state["screen"] = "searchUser"
                    st.session_state["target"] = None
                    st.success(f"Welcome back, {displayName}!")
                    st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

if st.session_state["screen"] == "homepage":
    st.title("Welcome to Dialogue")
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
        status, contacts = requestSupabase(
            "/rest/v1/profiles?select=id,displayName&order=displayName",
            accessToken=st.session_state["access_token"],
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
            targetName = st.selectbox(
                "select a user:",
                list(options),
                index=None,
                placeholder="search User...",
                key="contact_selector",
            )
            if targetName:
                st.session_state["screen"] = "chat"
                st.session_state["target"] = options[targetName]
                st.rerun()
    except Exception as exc:
        st.error(f"Could not load contacts: {exc}")

elif st.session_state["screen"] == "chat":
    with st.sidebar:
        if st.button("Back to Contacts"):
            st.session_state.pop("target", None)
            st.session_state.pop("contact_selector", None)
            st.session_state["screen"] = "searchUser"
            st.rerun()
        if st.button("Refresh Messages"):
            st.rerun()

    target = st.session_state["target"]
    currentUserId = st.session_state["user"]["id"]
    targetId = target["id"]
    st.title(f"Chat with {target['displayName'] or 'Unnamed user'}")

    messages = readMessages(st.session_state["access_token"], currentUserId, targetId)
    
    # Fetch all profiles to map user IDs to display names
    status, profiles = requestSupabase(
        "/rest/v1/profiles?select=id,displayName",
        accessToken=st.session_state["access_token"],
    )
    nameMap = {p["id"]: p.get("displayName") or "Unknown" for p in profiles} if status < 400 else {}
    # Add current user's name from session
    nameMap[currentUserId] = st.session_state["user"].get("user_metadata", {}).get("displayName", "You")
    
    for msg in messages:
        senderName = nameMap.get(msg["from"], "Unknown")
        isCurrentUser = msg["from"] == currentUserId
        dt = datetime.fromisoformat(msg["created_at"])
        timeStr = dt.astimezone().strftime("%Y-%m-%d %I:%M:%S %p")
        # timeStr = dt.strftime("%Y-%m-%d %H:%M:%S")
        with st.chat_message("user"):

            st.markdown(f"**{senderName}**")
            st.write(msg["message"])
            for fileInfo in msg.get("files") or []:
                fileUrl = asyncio.run(
                    createSignedUrl(
                        st.session_state["access_token"],
                        "files",
                        fileInfo["path"],
                    )
                )

                fileType = fileInfo.get("type", "")
                if fileType.startswith("image/"):
                    st.image(fileUrl, caption=fileInfo["name"])
                elif fileType.startswith("video/"):
                    st.video(fileUrl)
                    st.caption(fileInfo['name'])
                elif fileType.startswith("audio/"):
                    st.audio(fileUrl)
                    st.caption(fileInfo['name'])
                else:
                    st.markdown(f"[{fileInfo['name']}]({fileUrl})")
            
            st.caption(f"Sent at: {timeStr}")
    userInput = st.chat_input(
        "Say something",
        accept_file=True,
        accept_audio=True,
        key=f"chat_input_{targetId}",
    )
    #, file_type=["pdf", "png", "jpg", "txt"]
    if userInput is not None:
        try:
            messageText = userInput.text or ""
            files = list(userInput.files or [])
            fileInfos = []
            audioFile = userInput.audio
            if audioFile is not None:
                files.append(audioFile)

            for uploadedFile in files:
                fileBytes = uploadedFile.getvalue()
                filePath = f"{currentUserId}/{uploadedFile.name}"
                status, result = asyncio.run(uploadFile(
                    st.session_state["access_token"],
                    "files",
                    filePath,
                    fileBytes,
                    uploadedFile.type or "application/octet-stream",
                ))
                if status >= 400:
                    raise RuntimeError(result)
                fileInfos.append({
                    "name": uploadedFile.name,
                    "path": filePath,
                    "type": uploadedFile.type,
                    "size": uploadedFile.size,
                })

            if messageText.strip() or files:
                writeMessage(
                    messageText.strip(),
                    currentUserId,
                    target["id"],
                    st.session_state["access_token"],
                    fileInfos,
                )
                st.rerun()
        except Exception as exc:
            st.error(f"Could not send file: {exc}")
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
    st_autorefresh(interval=5000, key=f"msg_poll_{targetId}")
