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
        # Add new users here with plain passwords
    }
}

# ───────────────────────────────────────────────
# LOGIN / SIGNUP PAGE
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
                    st.success(f"Welcome {user['name']}! Loading translator...")
                    log = f"{datetime.now()} - Login: {username}"
                    st.write(log)
                    st.rerun()  # 1-click success
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
    # ───────────────────────────────────────────────
    # JOHNY TRANSLATOR (after login)
    # ───────────────────────────────────────────────

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    PRIMARY_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-1.5-flash"

    if "current_model" not in st.session_state:
        st.session_state.current_model = PRIMARY_MODEL

    model = genai.GenerativeModel(st.session_state.current_model)

    @retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=1, min=4, max=60))
    def safe_generate_content(prompt):
        return model.generate_content(prompt)

    # Glossary
    if "glossary" not in st.session_state:
        try:
            raw_url = "https://raw.githubusercontent.com/Juniorssv4/Johny-LOGIN/main/glossary.txt"
            response = requests.get(raw_url)
            response.raise_for_status()
            lines = response.text.splitlines()
            glossary_dict = {}
            for line in lines:
                line = line.strip()
                if line and ":" in line:
                    eng, lao = line.split(":", 1)
                    glossary_dict[eng.strip().lower()] = lao.strip()
            st.session_state.glossary = glossary_dict
        except:
            st.session_state.glossary = {}

    glossary = st.session_state.glossary

    def get_glossary_prompt():
        if glossary:
            terms = "\n".join([f"• {e.capitalize()} → {l}" for e, l in glossary.items()])
            return f"Use EXACTLY these terms:\n{terms}\n"
        return ""

    def translate_text(text, direction):
        if not text.strip():
            return ""
        target = "Lao" if direction == "English → Lao" else "English"
        prompt = f"""{get_glossary_prompt()}Translate ONLY the text to {target}.
Return ONLY the translation.

Text: {text}"""

        try:
            response = safe_generate_content(prompt)
            return response.text.strip()
        except RetryError as e:
            if "429" in str(e.last_attempt.exception()) or "quota" in str(e.last_attempt.exception()).lower():
                if st.session_state.current_model == PRIMARY_MODEL:
                    st.session_state.current_model = FALLBACK_MODEL
                    st.info("Rate limit — switched to fallback.")
                    global model
                    model = genai.GenerativeModel(FALLBACK_MODEL)
                    response = model.generate_content(prompt)
                    return response.text.strip()
            st.error("Timed out — try later.")
            return "[Failed — try later]"
        except Exception as e:
            st.error(f"API error: {str(e)}")
            return "[Failed — try again]"

    st.title("😊 Johny — NPA Lao Translator")

    direction = st.radio("Direction", ["English → Lao", "Lao → English"], horizontal=True)

    tab1, tab2 = st.tabs(["Translate Text", "Translate File"])

    with tab1:
        text = st.text_area("Enter text to translate", height=200)
        if st.button("Translate Text", type="primary"):
            with st.spinner("Translating..."):
                result = translate_text(text, direction)
                st.success("Translation:")
                st.write(result)

    with tab2:
        uploaded_file = st.file_uploader("Upload DOCX • XLSX • PPTX (max 50MB)", type=["docx", "xlsx", "pptx"])

        if uploaded_file:
            MAX_SIZE_MB = 50
            if uploaded_file.size > MAX_SIZE_MB * 1024 * 1024:
                st.error(f"File too large! Max {MAX_SIZE_MB}MB. Your file: {uploaded_file.size / (1024*1024):.1f}MB.")
            elif st.button("Translate File", type="primary"):
                with st.spinner("Translating file..."):
                    file_bytes = uploaded_file.read()
                    file_name = uploaded_file.name
                    ext = file_name.rsplit(".", 1)[-1].lower()
                    output = BytesIO()

                    total_elements = 0
                    elements_list = []

                    if ext == "docx":
                        doc = Document(BytesIO(file_bytes))
                        for p in doc.paragraphs:
                            if p.text.strip():
                                total_elements += 1
                                elements_list.append(("para", p))
                        for table in doc.tables:
                            for row in table.rows:
                                for cell in row.cells:
                                    for p in cell.paragraphs:
                                        if p.text.strip():
                                            total_elements += 1
                                            elements_list.append(("para", p))

                    elif ext == "xlsx":
                        wb = load_workbook(BytesIO(file_bytes))
                        for ws in wb.worksheets:
                            for row in ws.iter_rows():
                                for cell in row:
                                    if isinstance(cell.value, str) and cell.value.strip():
                                        total_elements += 1
                                        elements_list.append(("cell", cell))

                    elif ext == "pptx":
                        prs = Presentation(BytesIO(file_bytes))
                        for slide in prs.slides:
                            for shape in slide.shapes:
                                if shape.has_text_frame:
                                    for p in shape.text_frame.paragraphs:
                                        if p.text.strip():
                                            total_elements += 1
                                            elements_list.append(("para", p))

                    if total_elements == 0:
                        st.warning("No text found.")
                        st.stop()

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    translated_count = 0

                    for element_type, element in elements_list:
                        status_text.text(f"Translating... {translated_count}/{total_elements}")

                        if element_type == "para":
                            translated = translate_text(element.text, direction)
                            element.text = translated
                        elif element_type == "cell":
                            translated = translate_text(element.value, direction)
                            element.value = translated

                        translated_count += 1
                        progress_bar.progress(translated_count / total_elements)

                    status_text.text("Saving file...")
                    if ext == "docx":
                        doc.save(output)
                    elif ext == "xlsx":
                        wb.save(output)
                    elif ext == "pptx":
                        prs.save(output)

                    output.seek(0)

                    filename = f"TRANSLATED_{file_name}"
                    mime_type = "application/octet-stream"

                    st.success("Translation complete!")
                    st.info("Click below to download.")

                    st.download_button(
                        label="📥 DOWNLOAD TRANSLATED FILE NOW",
                        data=output,
                        file_name=filename,
                        mime=mime_type,
                        type="primary",
                        use_container_width=True,
                        key="download_" + str(time.time())
                    )

                    st.caption("Tip: Refresh or use Chrome if needed.")

    with st.expander("➕ Teach Johny a new term"):
        st.info("Edit glossary.txt in repo → add 'english:lao' → save.")
        st.code("Example:\nUXO:ລບຕ")

    st.caption(f"Glossary: {len(glossary)} terms • Model: {st.session_state.current_model}")

    # Logout button (1-click, instant return to login)
    if st.button("Logout"):
        st.session_state["authentication_status"] = False
        st.rerun()  # Instant logout
