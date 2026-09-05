import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import base64
import json
from datetime import datetime
from dotenv import load_dotenv
from streamlit_oauth import OAuth2Component
from groq import Groq


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# 1. CONFIGURATIONS & GROQ AI SETUP
# ==========================================

# Admin credentials should be stored in .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ==========================================
# GROQ AI RESPONSE FUNCTION
# ==========================================

def generate_ai_response(prompt_text, topic):

    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is missing in your .env file."

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        system_instruction = (
            "You are a helpful Personal AI Assistant. "

            "1. Strictly detect the language/style of the user's query "
            "(Tanglish, Tamil, or English). "

            "2. Reply directly in that exact same language/style. "

            "3. Answer the user's question accurately without unnecessary fluff. "

            "4. If the user asks a technical question, explain it clearly "
            "with simple examples when useful."
        )

        response = client.chat.completions.create(

            # CURRENT GROQ MODEL
            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": (
                        f"Chat Topic: {topic}\n"
                        f"User Question: {prompt_text}"
                    )
                }
            ],

            # Moderate response length
            max_tokens=2048
        )

        if response and response.choices:

            return response.choices[0].message.content

        return "API Error: No response generated."

    except Exception as e:

        return f"Groq API Error: {str(e)}"


# ==========================================
# ADMIN LOGIN VERIFICATION
# ==========================================

def verify_admin(username, password):

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        return False

    def clean_text(text):

        return re.sub(
            r'[^a-zA-Z0-9]',
            '',
            text
        ).lower()

    return (
        clean_text(username) == clean_text(ADMIN_USERNAME)
        and
        clean_text(password) == clean_text(ADMIN_PASSWORD)
    )


# ==========================================
# GOOGLE JWT DECODER
# ==========================================

def decode_jwt(token):

    try:

        payload_part = token.split('.')[1]

        payload_part += '=' * (
            -len(payload_part) % 4
        )

        decoded_bytes = base64.urlsafe_b64decode(
            payload_part
        )

        return json.loads(
            decoded_bytes.decode('utf-8')
        )

    except Exception:

        return {}


# ==========================================
# 2. DATABASE SETUP
# ==========================================

def init_db():

    conn = sqlite3.connect(
        'analytics.db',
        check_same_thread=False
    )

    cursor = conn.cursor()

    # Users table
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users
        (
            email TEXT PRIMARY KEY,
            password TEXT
        )
        '''
    )

    # Usage logs table
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS usage_logs
        (
            user_email TEXT,
            topic TEXT,
            timestamp DATETIME
        )
        '''
    )

    conn.commit()
    conn.close()


init_db()


# ==========================================
# REGISTER USER
# ==========================================

def register_user(email, password):

    try:

        conn = sqlite3.connect(
            'analytics.db',
            check_same_thread=False
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (email, password)
            VALUES (?, ?)
            """,
            (
                email,
                password
            )
        )

        conn.commit()
        conn.close()

        return True

    except sqlite3.IntegrityError:

        return False


# ==========================================
# NORMAL USER LOGIN
# ==========================================

def verify_normal_user(email, password):

    conn = sqlite3.connect(
        'analytics.db',
        check_same_thread=False
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        AND password = ?
        """,
        (
            email,
            password
        )
    )

    user = cursor.fetchone()

    conn.close()

    return user is not None


# ==========================================
# UPDATE PASSWORD
# ==========================================

def update_password(email, new_password):

    conn = sqlite3.connect(
        'analytics.db',
        check_same_thread=False
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET password = ?
        WHERE email = ?
        """,
        (
            new_password,
            email
        )
    )

    affected = cursor.rowcount

    conn.commit()
    conn.close()

    return affected > 0


# ==========================================
# LOG USER ACTIVITY
# ==========================================

def log_user_activity(email, topic):

    try:

        conn = sqlite3.connect(
            'analytics.db',
            check_same_thread=False
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usage_logs
            (user_email, topic, timestamp)
            VALUES (?, ?, ?)
            """,
            (
                email,
                topic,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()
        conn.close()

    except Exception as e:

        print(
            f"Logging Error: {e}"
        )


# ==========================================
# FETCH ANALYTICS
# ==========================================

def fetch_analytics():

    conn = sqlite3.connect(
        'analytics.db',
        check_same_thread=False
    )

    users_count = pd.read_sql_query(
        """
        SELECT COUNT(DISTINCT user_email) as total
        FROM usage_logs
        """,
        conn
    ).iloc[0]['total']

    topics_data = pd.read_sql_query(
        """
        SELECT topic,
               COUNT(*) as usage_count
        FROM usage_logs
        GROUP BY topic
        """,
        conn
    )

    recent_activity = pd.read_sql_query(
        """
        SELECT user_email,
               timestamp,
               topic
        FROM usage_logs
        ORDER BY timestamp DESC
        LIMIT 50
        """,
        conn
    )

    conn.close()

    return (
        users_count,
        topics_data,
        recent_activity
    )


# ==========================================
# PASSWORD STRENGTH
# ==========================================

def validate_password_strength(password):

    has_len = len(password) >= 10

    has_digit = bool(
        re.search(
            r'[0-9]',
            password
        )
    )

    has_special = bool(
        re.search(
            r'[!@#$%^&*(),.?":{}|<>]',
            password
        )
    )

    has_upper = bool(
        re.search(
            r'[A-Z]',
            password
        )
    )

    return (
        has_len,
        has_digit,
        has_special,
        has_upper
    )


# ==========================================
# SIGNUP PAGE
# ==========================================

@st.fragment
def render_signup_page():

    st.markdown(
        "### 📝 Create New Account"
    )

    new_email = st.text_input(
        "Enter Email / Username",
        key="signup_email"
    )

    new_password = st.text_input(
        "Create Password",
        type="password",
        key="signup_pass"
    )

    (
        l_check,
        d_check,
        s_check,
        u_check
    ) = validate_password_strength(
        new_password
    )

    st.markdown(
        "**Password Requirements:**"
    )

    st.markdown(
        f"{'✅' if l_check else '❌'} "
        "At least 10 characters"
    )

    st.markdown(
        f"{'✅' if d_check else '❌'} "
        "Contains at least one number (0-9)"
    )

    st.markdown(
        f"{'✅' if s_check else '❌'} "
        "Contains at least one special character (!@#$...)"
    )

    st.markdown(
        f"{'✅' if u_check else '❌'} "
        "Contains at least one uppercase letter"
    )

    st.divider()

    if st.button(
        "Sign Up",
        use_container_width=True,
        key="signup_btn"
    ):

        if not new_email or not new_password:

            st.warning(
                "Please fill in all fields."
            )

        elif not (
            l_check
            and d_check
            and s_check
            and u_check
        ):

            st.error(
                "Please meet all password requirements!"
            )

        else:

            if register_user(
                new_email,
                new_password
            ):

                st.success(
                    "Account created successfully! "
                    "Please go back and login."
                )

            else:

                st.error(
                    "Username/Email already exists!"
                )

    if st.button(
        "← Back to Login",
        key="back_from_signup",
        use_container_width=True
    ):

        st.session_state[
            "current_page"
        ] = "login"

        st.rerun()


# ==========================================
# FORGOT PASSWORD PAGE
# ==========================================

@st.fragment
def render_forgot_page():

    st.markdown(
        "### 🔑 Reset Password"
    )

    f_email = st.text_input(
        "Enter your registered Email / Username",
        key="forgot_email"
    )

    f_new_pass = st.text_input(
        "New Password",
        type="password",
        key="forgot_pass"
    )

    (
        l_check,
        d_check,
        s_check,
        u_check
    ) = validate_password_strength(
        f_new_pass
    )

    st.markdown(
        "**Password Requirements:**"
    )

    st.markdown(
        f"{'✅' if l_check else '❌'} "
        "At least 10 characters"
    )

    st.markdown(
        f"{'✅' if d_check else '❌'} "
        "Contains at least one number (0-9)"
    )

    st.markdown(
        f"{'✅' if s_check else '❌'} "
        "Contains at least one special character (!@#$...)"
    )

    st.markdown(
        f"{'✅' if u_check else '❌'} "
        "Contains at least one uppercase letter"
    )

    st.divider()

    if st.button(
        "Update Password",
        use_container_width=True,
        key="forgot_btn"
    ):

        if not f_email or not f_new_pass:

            st.warning(
                "Please fill in all fields."
            )

        elif not (
            l_check
            and d_check
            and s_check
            and u_check
        ):

            st.error(
                "Please meet all password requirements!"
            )

        else:

            if update_password(
                f_email,
                f_new_pass
            ):

                st.success(
                    "Password updated successfully! "
                    "Please login with your new password."
                )

            else:

                st.error(
                    "Email not found in database!"
                )

    if st.button(
        "← Back to Login",
        key="back_from_forgot",
        use_container_width=True
    ):

        st.session_state[
            "current_page"
        ] = "login"

        st.rerun()


# ==========================================
# 3. MAIN APP & UI ROUTING
# ==========================================

def main():

    # ======================================
    # CUSTOM CSS
    # ======================================

    st.markdown(
        """
        <style>

        .stApp {
            background:
            linear-gradient(
                to bottom,
                #1e3c72,
                #2a5298
            );

            color: white;
        }

        h1, h2, h3, h4, h5, h6,
        p, div, span, label {

            color: white !important;
        }

        .stTextInput>div>div>input {

            background-color: #2b3035;

            color: white;
        }

        [data-testid="stChatMessage"] {

            background-color:
            rgba(25, 45, 85, 0.4)
            !important;

            border-radius: 12px;

            border:
            1px solid
            rgba(255, 255, 255, 0.08);

            padding: 12px;

            margin-bottom: 10px;
        }

        [data-testid="stChatMessageAvatar"] {

            background: transparent !important;

            border: none !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    # ======================================
    # SESSION STATE
    # ======================================

    if "logged_in" not in st.session_state:

        st.session_state[
            "logged_in"
        ] = False

    if "user_role" not in st.session_state:

        st.session_state[
            "user_role"
        ] = None

    if "current_page" not in st.session_state:

        st.session_state[
            "current_page"
        ] = "login"


    # ======================================
    # GOOGLE OAUTH
    # ======================================

    if CLIENT_ID and CLIENT_SECRET:

        oauth2 = OAuth2Component(

            client_id=CLIENT_ID,

            client_secret=CLIENT_SECRET,

            authorize_endpoint=(
                "https://accounts.google.com/"
                "o/oauth2/v2/auth"
            ),

            token_endpoint=(
                "https://oauth2.googleapis.com/token"
            )
        )

    else:

        oauth2 = None


    # ======================================
    # LOGGED-IN USERS
    # ======================================

    if st.session_state["logged_in"]:


        # ==================================
        # ADMIN DASHBOARD
        # ==================================

        if (
            st.session_state["user_role"]
            == "admin"
        ):

            st.title(
                "🔒 Admin Analytics Dashboard"
            )

            if st.button("Logout"):

                st.session_state[
                    "logged_in"
                ] = False

                st.session_state[
                    "user_role"
                ] = None

                st.rerun()

            st.divider()

            try:

                (
                    total_users,
                    topics_data,
                    recent_activity
                ) = fetch_analytics()

                st.metric(
                    label="Total Unique Users",
                    value=total_users
                )

                st.subheader(
                    "Topic Usage Distribution"
                )

                if not topics_data.empty:

                    st.bar_chart(
                        topics_data.set_index(
                            "topic"
                        )
                    )

                else:

                    st.info(
                        "No topic data available yet."
                    )

                st.subheader(
                    "Recent Activity Logs"
                )

                if not recent_activity.empty:

                    st.dataframe(
                        recent_activity,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "No recent activity recorded yet."
                    )

            except Exception as e:

                st.error(
                    f"Database Error: {e}"
                )


        # ==================================
        # NORMAL USER CHAT
        # ==================================

        elif (
            st.session_state["user_role"]
            == "user"
        ):

            uploaded_file_content = (
                st.session_state.get(
                    "uploaded_doc_text",
                    None
                )
            )


            # ==============================
            # SIDEBAR
            # ==============================

            with st.sidebar:

                st.markdown(
                    "### 📂 Categories"
                )

                selected_topic = st.radio(

                    "Choose Chat Topic:",

                    [
                        "General",
                        "Movies",
                        "Cyber Security",
                        "Document Chat (PDF/Excel)"
                    ]
                )


                # ==========================
                # DOCUMENT UPLOAD
                # ==========================

                if (
                    selected_topic
                    == "Document Chat (PDF/Excel)"
                ):

                    st.divider()

                    st.markdown(
                        "### 📄 Upload Document"
                    )

                    uploaded_file = st.file_uploader(

                        "Upload PDF or Excel file",

                        type=[
                            "pdf",
                            "xlsx",
                            "xls",
                            "csv"
                        ],

                        max_upload_size=1024,

                        help=(
                            "Supports high-capacity "
                            "files up to 1GB"
                        )
                    )


                    if uploaded_file is not None:

                        try:

                            if uploaded_file.name.endswith(
                                ".csv"
                            ):

                                df_file = pd.read_csv(
                                    uploaded_file
                                )

                                uploaded_file_content = (
                                    df_file.to_string()
                                )


                            elif uploaded_file.name.endswith(
                                (".xlsx", ".xls")
                            ):

                                df_file = pd.read_excel(
                                    uploaded_file
                                )

                                uploaded_file_content = (
                                    df_file.to_string()
                                )


                            elif uploaded_file.name.endswith(
                                ".pdf"
                            ):

                                uploaded_file_content = (
                                    f"Uploaded PDF File Name: "
                                    f"{uploaded_file.name}. "
                                    f"Content ready for Q&A."
                                )


                            st.session_state[
                                "uploaded_doc_text"
                            ] = uploaded_file_content

                            st.success(
                                f"Loaded successfully: "
                                f"{uploaded_file.name}"
                            )

                        except Exception as ex:

                            st.error(
                                f"Error reading file: {ex}"
                            )


                st.divider()


                # ==========================
                # LOGOUT
                # ==========================

                if st.button(
                    "🚪 Logout",
                    use_container_width=True
                ):

                    st.session_state[
                        "logged_in"
                    ] = False

                    st.session_state[
                        "user_role"
                    ] = None

                    st.session_state.pop(
                        "messages",
                        None
                    )

                    st.session_state.pop(
                        "uploaded_doc_text",
                        None
                    )

                    st.rerun()


            # ==================================
            # CHAT UI
            # ==================================

            st.markdown(
                "## 🤖 Personal AI Chat Bot"
            )


            raw_user = st.session_state.get(
                "user_email",
                "User"
            )

            display_name = st.session_state.get(
                "user_display_name",
                None
            )


            if not display_name:

                display_name = (
                    raw_user.split("@")[0].capitalize()
                    if "@" in raw_user
                    else raw_user.capitalize()
                )


            st.write(
                f"Welcome, **{display_name}**! 👋"
            )


            # ==================================
            # TOPIC PROMPTS
            # ==================================

            topic_prompts = {

                "General":
                    "Hello! How can I help you "
                    "with general questions today?",

                "Movies":
                    "Explore Tamil cinema thrillers, "
                    "cyber-thrillers, and sci-fi films! "
                    "What would you like to know?",

                "Cyber Security":
                    "Welcome to Cyber Security mode. "
                    "Ask me about network threats, "
                    "encryption, or security protocols.",

                "Document Chat (PDF/Excel)":
                    "Welcome to Document Chat! "
                    "Upload your document in the sidebar "
                    "and ask me anything about it."
            }


            # ==================================
            # MESSAGE HISTORY
            # ==================================

            if "messages" not in st.session_state:

                st.session_state.messages = []


            if not st.session_state.messages:

                initial_msg = topic_prompts.get(

                    selected_topic,

                    "Hello there! "
                    "How can I help you today?"
                )

                st.session_state.messages.append(

                    {
                        "role": "assistant",
                        "content": initial_msg
                    }
                )


            # ==================================
            # DISPLAY MESSAGES
            # ==================================

            for message in st.session_state.messages:

                avatar_icon = (
                    "👤"
                    if message["role"] == "user"
                    else "✨"
                )

                with st.chat_message(
                    message["role"],
                    avatar=avatar_icon
                ):

                    st.markdown(
                        message["content"]
                    )


            # ==================================
            # CHAT INPUT
            # ==================================

            if prompt := st.chat_input(
                "Type your message here..."
            ):

                current_user_email = (
                    st.session_state.get(
                        "user_email",
                        "unknown_user"
                    )
                )


                # Log activity
                log_user_activity(
                    current_user_email,
                    selected_topic
                )


                # Add user message
                st.session_state.messages.append(

                    {
                        "role": "user",
                        "content": prompt
                    }
                )


                with st.chat_message(
                    "user",
                    avatar="👤"
                ):

                    st.markdown(prompt)


                # ==================================
                # AI RESPONSE
                # ==================================

                with st.chat_message(
                    "assistant",
                    avatar="✨"
                ):

                    with st.spinner(
                        "AI is thinking..."
                    ):


                        if (
                            selected_topic
                            == "Document Chat (PDF/Excel)"
                            and uploaded_file_content
                        ):

                            context_prompt = (

                                "Document Context:\n"

                                + uploaded_file_content

                                + "\n\nUser Question:\n"

                                + prompt
                            )

                        else:

                            context_prompt = prompt


                        bot_response = (
                            generate_ai_response(
                                context_prompt,
                                selected_topic
                            )
                        )


                    st.markdown(
                        bot_response
                    )


                    st.session_state.messages.append(

                        {
                            "role": "assistant",
                            "content": bot_response
                        }
                    )


    # ======================================
    # LOGIN PAGE
    # ======================================

    else:

        _, col_center, _ = st.columns(
            [1, 2, 1]
        )


        with col_center:

            # ==================================
            # LOGIN
            # ==================================

            if (
                st.session_state[
                    "current_page"
                ]
                == "login"
            ):

                st.markdown(
                    "### © AI Personal Chatbot"
                )

                st.markdown(
                    "**Sign in to start chatting.**"
                )


                with st.form(
                    "login_form"
                ):

                    username_input = st.text_input(
                        "Username / Email"
                    )

                    password_input = st.text_input(
                        "Password",
                        type="password"
                    )

                    submitted = (
                        st.form_submit_button(
                            "Login",
                            use_container_width=True
                        )
                    )


                    if submitted:

                        # ==========================
                        # ADMIN LOGIN
                        # ==========================

                        if verify_admin(
                            username_input,
                            password_input
                        ):

                            st.session_state[
                                "logged_in"
                            ] = True

                            st.session_state[
                                "user_role"
                            ] = "admin"

                            st.session_state[
                                "user_email"
                            ] = username_input

                            st.session_state[
                                "user_display_name"
                            ] = "Admin"

                            st.rerun()


                        # ==========================
                        # NORMAL USER LOGIN
                        # ==========================

                        elif verify_normal_user(
                            username_input,
                            password_input
                        ):

                            st.session_state[
                                "logged_in"
                            ] = True

                            st.session_state[
                                "user_role"
                            ] = "user"

                            st.session_state[
                                "user_email"
                            ] = username_input

                            st.session_state[
                                "user_display_name"
                            ] = (
                                username_input.split("@")[0].capitalize()
                                if "@"
                                in username_input
                                else username_input.capitalize()
                            )

                            st.rerun()


                        else:

                            st.error(
                                "Invalid credentials "
                                "or user not found."
                            )


                # ==================================
                # SIGNUP + FORGOT PASSWORD
                # ==================================

                b_col1, b_col2 = st.columns(2)


                with b_col1:

                    if st.button(
                        "Create Account",
                        key="goto_signup",
                        use_container_width=True
                    ):

                        st.session_state[
                            "current_page"
                        ] = "signup"

                        st.rerun()


                with b_col2:

                    if st.button(
                        "Forgot password?",
                        key="goto_forgot",
                        use_container_width=True
                    ):

                        st.session_state[
                            "current_page"
                        ] = "forgot"

                        st.rerun()


                st.markdown(
                    """
                    <p style='
                    text-align: center;
                    font-weight: bold;
                    margin: 15px 0;
                    '>
                    OR
                    </p>
                    """,
                    unsafe_allow_html=True
                )


                # ==================================
                # GOOGLE LOGIN
                # ==================================

                if oauth2:

                    try:

                        result = (
                            oauth2.authorize_button(

                                name="Continue with Google",

                                icon=(
                                    "https://www.google.com/"
                                    "favicon.ico"
                                ),

                                redirect_uri=(
                                    "http://localhost:8501"
                                ),

                                scope=(
                                    "openid email profile"
                                ),

                                key="google_oauth_button"
                            )
                        )


                        if (
                            result
                            and "token" in result
                        ):

                            token_info = (
                                result["token"]
                            )

                            id_token = (
                                token_info.get(
                                    "id_token"
                                )
                            )


                            user_info = (
                                decode_jwt(
                                    id_token
                                )
                                if id_token
                                else {}
                            )


                            g_email = user_info.get(
                                "email",
                                "google_user@gmail.com"
                            )


                            g_name = user_info.get(

                                "name",

                                g_email.split(
                                    "@"
                                )[0].capitalize()
                            )


                            st.session_state[
                                "logged_in"
                            ] = True

                            st.session_state[
                                "user_role"
                            ] = "user"

                            st.session_state[
                                "user_email"
                            ] = g_email

                            st.session_state[
                                "user_display_name"
                            ] = g_name

                            st.rerun()


                    except Exception as e:

                        st.error(
                            f"Google Login Error: {e}"
                        )


                else:

                    st.error(
                        "Google Client ID or Secret "
                        "missing in .env file!"
                    )


            # ==================================
            # SIGNUP PAGE
            # ==================================

            elif (
                st.session_state[
                    "current_page"
                ]
                == "signup"
            ):

                render_signup_page()


            # ==================================
            # FORGOT PASSWORD PAGE
            # ==================================

            elif (
                st.session_state[
                    "current_page"
                ]
                == "forgot"
            ):

                render_forgot_page()


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    main()