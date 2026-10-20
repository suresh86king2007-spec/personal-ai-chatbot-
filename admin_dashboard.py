import streamlit as st
import sqlite3
import pandas as pd
import re

ADMIN_USERNAME = "suresh kumar 8300940712 2006"
ADMIN_PASSWORD = "SURESH KUMAR 09"

def verify_credentials(username, password):
    def clean_text(text):
        return re.sub(r'[^a-zA-Z0-9]', '', text).lower()
    return clean_text(username) == clean_text(ADMIN_USERNAME) and clean_text(password) == clean_text(ADMIN_PASSWORD)

def fetch_analytics():
    conn = sqlite3.connect('analytics.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usage_logs 
                      (user_email TEXT, topic TEXT, timestamp DATETIME)''')
    conn.commit()

    users_count = pd.read_sql_query("SELECT COUNT(DISTINCT user_email) as total FROM usage_logs", conn).iloc[0]['total']
    topics_data = pd.read_sql_query("SELECT topic, COUNT(*) as usage_count FROM usage_logs GROUP BY topic", conn)
    recent_activity = pd.read_sql_query("SELECT timestamp, topic FROM usage_logs ORDER BY timestamp DESC LIMIT 50", conn)
    
    conn.close()
    return users_count, topics_data, recent_activity

def run_admin_page():
    st.set_page_config(page_title="Admin Dashboard", layout="centered")
    st.title("🔒 Admin Analytics Dashboard")

    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        st.subheader("Admin Login")
        with st.form("login_form"):
            username_input = st.text_input("Enter Admin Username")
            password_input = st.text_input("Enter Admin Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if verify_credentials(username_input, password_input):
                    st.session_state["admin_logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
    else:
        st.success("Logged in successfully!")
        if st.button("Logout"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

        st.divider()
        st.header("📊 Chatbot Usage Metrics")

        try:
            total_users, topics_data, recent_activity = fetch_analytics()
            st.metric(label="Total Unique Users", value=total_users)
            
            st.subheader("Topic Usage Distribution")
            if not topics_data.empty:
                st.bar_chart(topics_data.set_index('topic'))
            else:
                st.info("No topic data available yet.")

            st.subheader("Recent Activity (Time & Topic)")
            if not recent_activity.empty:
                st.dataframe(recent_activity, use_container_width=True, hide_index=True)
            else:
                st.info("No recent activity found.")
        except Exception as e:
             st.error(f"Database Error: {e}")

if __name__ == "__main__":
    run_admin_page()