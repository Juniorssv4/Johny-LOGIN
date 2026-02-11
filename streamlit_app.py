import streamlit as st
import smtplib
from email.message import EmailMessage
from datetime import datetime
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
import requests
from io import BytesIO
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
import json
import uuid

# ───────────────────────────────────────────────
# APPROVED USERS (plain passwords – testing/private use only)
# ───────────────────────────────────────────────
credentials = {
    'usernames': {
        'admin': {
            'name': 'Admin',
            'password': 'admin123',
            'email': 'sisouvanhjunior@gmail.com'
        },
        'juniorssv4': {
            'name': 'Junior SSV4',
            'password': 'Junior76755782@',
            'email': 'phosis667@npaid.org'
        }
    }
}

# Load Firebase config from GitHub raw file
FIREBASE_RAW_URL = "https://raw.githubusercontent.com/Juniorssv4/YOUR_REPO_NAME/main/firebase_config.json"
# CHANGE YOUR_REPO_NAME to your actual repo name (e.g. Johny-LOGIN)

try:
    config_response = requests.get(FIREBASE_RAW_URL)
    if config_response.status_code == 200:
        FIREBASE_CONFIG = config_response.json()
    else:
        FIREBASE_CONFIG = None
except:
    FIREBASE_CONFIG = None

if FIREBASE_CONFIG is None:
    st.warning("Firebase config not loaded. Using locked mode (no persistence).")

# Firebase database URL
if FIREBASE_CONFIG:
    FIREBASE_URL = f"{FIREBASE_CONFIG['databaseURL']}/logins.json"
else:
    FIREBASE_URL = None

# Persistent device ID
def get_device_id():
    if 'device_id' not in st.session_state:
        st.session_state['device_id'] = str(uuid.uuid4())
    return st.session_state['device_id']

device_id = get_device_id()

# Load logins from Firebase (if config loaded)
logins = {}
if FIREBASE_URL:
    try:
        r = requests.get(FIREBASE_URL)
        logins = r.json() if r.status_code == 200 else {}
    except:
        logins = {}

# Auto-login if device is saved
if device_id in logins:
    username = logins[device_id]
    if username in credentials['usernames']:
        st.session_state["authentication_status"] = True
        st.session_state["name"] = credentials['usernames'][username]['name']
        st.session_state["username"] = username

# ───────────────────────────────────────────────
# LOGIN / SIGN UP PAGE
# ───────────────────────────────────────────────
if not st.session_state.get("authentication_status"):
    st.title("Johny - Login / Sign Up")

    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username in credentials['usernames']:
                user = credentials['usernames'][username]
                if password == user['password']:
                    st.session_state["authentication_status"] = True
                    st.session_state["name"] = user['name']
                    st.session_state["username"] = username
                    # Save to Firebase
                    if FIREBASE_URL:
                        logins = load_logins()
                        logins[device_id] = username
                        requests.put(FIREBASE_URL, json=logins)
                    st.success(f"Welcome {user['name']}! Loading translator...")
                    st.rerun()
                else:
                    st.error("Incorrect password")
            else:
                st.error("Username not found")

    with tab_signup:
        st.subheader("Sign Up (Request Approval)")
        st.info("Sign up — request sent to sisouvanhjunior@gmail.com for approval.")
        new_username = st.text_input("Choose username")
        new_email = st.text_input("Your email")
        new_password = st.text_input("Choose password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")

        if st.button("Sign Up"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif new_username in credentials['usernames']:
                st.error("Username already taken")
            else:
                msg = EmailMessage()
                msg['Subject'] = "New Johny Signup Request"
                msg['From'] = st.secrets["EMAIL_USER"]
                msg['To'] = "sisouvanhjunior@gmail.com"
                msg.set_content(f"New signup:\nUsername: {new_username}\nEmail: {new_email}\nPassword: {new_password}\nApprove by adding to credentials['usernames'] with plain password.")

                try:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
                        smtp.send_message(msg)
                    st.success("Request sent! Wait for admin approval.")
                except Exception as e:
                    st.error(f"Email failed: {str(e)}")

else:
    # Translator code (your existing translator section goes here)
    # ... paste your translator code here ...

    if st.button("Logout"):
        st.session_state["authentication_status"] = False
        st.rerun()
