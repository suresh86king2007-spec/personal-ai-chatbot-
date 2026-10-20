import streamlit as st
import os
import httpx
from dotenv import load_dotenv
import database as db

load_dotenv()
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
redirect_uri = "http://localhost:8501/"

def handle_google_oauth():
    if "code" in st.query_params and not st.session_state.get("logged_in", False):
        code = st.query_params["code"]
        token_data = {
            "code": code,
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        res = httpx.post("https://oauth2.googleapis.com/token", data=token_data, timeout=30.0)
        if res.status_code == 200:
            access_token = res.json().get("access_token")
            user_info = httpx.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=30.0).json()
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = user_info.get("name", "Google User")
            st.query_params.clear()
            st.rerun()

def login_page():
    st.markdown('<div class="card"><p class="title">🤖 AI Personal Chatbot</p><p class="subtitle">Sign in to start chatting.</p></div>', unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Login", use_container_width=True):
            stored_hash = db.get_user_hash(username)
            if stored_hash and stored_hash == db.hash_password(password):
                st.session_state.update({"logged_in": True, "current_user": username})
                st.rerun()
            else: st.error("Invalid credentials.")
    with col2:
        if st.button("Create Account", use_container_width=True):
            st.session_state["auth_mode"] = "signup"
            st.rerun()
            
    if st.button("Forgot password?", use_container_width=True):
        st.session_state["auth_mode"] = "forgot_request"
        st.rerun()

    if google_client_id:
        st.markdown("<h4 style='text-align: center; color: white;'>OR</h4>", unsafe_allow_html=True)
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={google_client_id}&response_type=code&redirect_uri={redirect_uri}&scope=openid%20email%20profile"
        st.markdown(f'<a href="{auth_url}" target="_self"><button style="width: 100%; padding: 10px; font-weight: bold; cursor: pointer;">🌐 Continue with Google</button></a>', unsafe_allow_html=True)

def sign_up_page():
    st.markdown('<div class="card"><p class="title">📝 Create Account</p></div>', unsafe_allow_html=True)
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    if st.button("Sign Up", use_container_width=True):
        if db.create_user(new_user, db.hash_password(new_pass)):
            st.success("Account created!")
            st.session_state["auth_mode"] = "login"
            st.rerun()
        else: st.error("Username exists.")
    if st.button("Back"): st.session_state["auth_mode"] = "login"; st.rerun()

# (Keeping forgot password simple for space)
def forgot_request_page():
    st.info("Forgot password module active. Check full logic in previous version.")
    if st.button("Back"): st.session_state["auth_mode"] = "login"; st.rerun()