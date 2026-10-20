import sqlite3
import hashlib
import os
import csv
import httpx
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

load_dotenv()
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# --- SQLite User DB ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)")
    cur.execute("SELECT password_hash FROM users WHERE username = ?", ("admin",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                    ("admin", hashlib.sha256("admin123".encode()).hexdigest()))
    conn.commit()
    conn.close()

def get_user_hash(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def create_user(username: str, password_hash: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_password(username: str, password_hash: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- FAISS DB & Custom Embedder ---
class CustomGoogleEmbeddings(Embeddings):
    def __init__(self, api_key):
        self.api_key = api_key
    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]
    def embed_query(self, text):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}}
        try:
            res = httpx.post(url, json=payload, timeout=15.0)
            if res.status_code == 200:
                return res.json()["embedding"]["values"]
            return [0.0] * 768 
        except Exception:
            return [0.0] * 768

embeddings = CustomGoogleEmbeddings(api_key=gemini_api_key) if gemini_api_key else None

def get_or_create_vector_db(csv_file, db_folder_name):
    if os.path.exists(db_folder_name):
        return FAISS.load_local(db_folder_name, embeddings, allow_dangerous_deserialization=True)
    docs = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                docs.append(Document(page_content=" | ".join(row)))
        if docs:
            db = FAISS.from_documents(docs, embeddings)
            db.save_local(db_folder_name)
            return db
    except FileNotFoundError:
        st.error(f"Error: {csv_file} file kidaikala!")
    return None