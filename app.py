# ============================================================
# AI PERSONAL CHATBOT
# SINGLE FILE : app.py
# ============================================================

# ============================================================
# 1. IMPORTS
# ============================================================

import os
import sys
import json
import sqlite3
import subprocess
import secrets
import time
import hmac
import hashlib
import re
import asyncio
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

import streamlit as st
import pandas as pd
import requests

from dotenv import load_dotenv
from google import genai
from google.genai import types

# MCP dependency: pip install -U "mcp[cli]" httpx2

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# ============================================================
# 2. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Personal AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 3. PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

# Separate API key for image generation.
IMAGE_API_KEY = os.getenv(
    "IMAGE_API_KEY",
    ""
).strip()

# Hugging Face text-to-image model.
IMAGE_MODEL = os.getenv(
    "IMAGE_MODEL",
    "black-forest-labs/FLUX.1-schnell"
).strip()

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "admin"
).strip()

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    "admin123"
).strip()

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    ""
).strip()

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET",
    ""
).strip()

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8501"
).strip()

DB_FILE = BASE_DIR / "analytics.db"

MCP_CONFIG_FILE = BASE_DIR / "mcp_servers.json"

TMDB_MCP_FILE = BASE_DIR / "tmdb_mcp_server.py"

TMDB_API_TOKEN = os.getenv("TMDB_API_TOKEN", "").strip()


# ============================================================
# 4. DARK UI / CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --bg:#0e1016;
        --panel:#11141c;
        --panel-blue:#171a23;
        --panel-blue-2:#20232d;
        --border:#343743;
        --text:#f4f4f5;
        --muted:#a6a8b3;
        --accent:#ff4b4b;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background:#0e1016 !important;
        color:var(--text) !important;
    }
    .stApp { background:#0e1016 !important; color:var(--text) !important; }
    [data-testid="stHeader"] { background:#0e1016 !important; }
    [data-testid="stToolbar"] { background:transparent !important; }
    [data-testid="stSidebar"] {
        background:#11141c !important;
        border-right:1px solid #2c2f38 !important;
    }
    [data-testid="stSidebar"] * { color:var(--text) !important; }

    .main-title { font-size:34px; font-weight:700; color:var(--text); margin-bottom:5px; }
    .sub-title { color:var(--muted); font-size:16px; margin-bottom:20px; }
    .info-card { padding:18px; border-radius:14px; border:1px solid var(--border); background:var(--panel); margin-bottom:15px; }
    .small-text { color:var(--muted); font-size:13px; }

    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        background:#ff4b4b !important;
        color:#f4f4f5 !important;
        border:1px solid #3a3d47 !important;
        border-radius:10px !important;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background:#ff5c5c !important;
        border-color:#555866 !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background:#262932 !important;
        border-color:#343743 !important;
        color:#f4f4f5 !important;
    }
    input, textarea { color:#f4f4f5 !important; background:#262932 !important; }
    input::placeholder, textarea::placeholder { color:#a6a8b3 !important; opacity:1 !important; }
    label, [data-testid="stWidgetLabel"] p { color:#f4f4f5 !important; }

    [data-testid="stChatMessage"] {
        background:#171a23 !important;
        border:1px solid #343743 !important;
        border-radius:14px !important;
        margin-bottom:10px !important;
    }
    [data-testid="stChatMessage"] * { color:#f4f4f5 !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 {
        color:#f4f4f5 !important;
    }

    [data-testid="stChatInput"] {
        background:#11141c !important;
        border:1px solid #343743 !important;
        border-radius:14px !important;
    }
    [data-testid="stChatInput"] textarea {
        background:#262932 !important;
        color:#f4f4f5 !important;
    }

    .mcp-card { padding:18px; border-radius:16px; background:#171a23; border:1px solid #343743; margin-bottom:14px; }
    .login-card { padding:24px; border-radius:18px; background:#11141c; border:1px solid #343743; box-shadow:0 8px 30px rgba(0,0,0,.25); }
    </style>
    """, unsafe_allow_html=True
)


# ============================================================
# 5. SESSION STATE
# ============================================================

DEFAULT_SESSION = {

    "logged_in": False,

    "user_email": None,

    "is_admin": False,

    "current_page": "general",

    "general_messages": [],

    "movie_messages": [],

    "image_messages": [],

    "document_messages": [],

    "uploaded_document_name": None,

    "uploaded_document_text": "",

    "response_language": "Auto Detect",

    "response_style": "Normal",

    "show_timestamps": True,

    "google_search_enabled": True,

    "mcp_servers": {},

    "google_oauth_state": None

}


for key, value in DEFAULT_SESSION.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# 6. GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client():

    if not GEMINI_API_KEY:

        return None

    try:

        return genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception:

        return None


client = get_gemini_client()


# ============================================================
# 7. DATABASE
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(
        DB_FILE,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_database():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            topic TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )

    conn.commit()

    conn.close()


init_database()


# ============================================================
# 8. USER REGISTRATION
# ============================================================

def register_user(email, password):

    email = email.strip().lower()

    if not email or not password:

        return False, "Email and password are required."

    conn = get_db_connection()

    try:

        conn.execute(
            """
            INSERT INTO users(email, password)
            VALUES (?, ?)
            """,
            (
                email,
                password
            )
        )

        conn.commit()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:

        return False, "Email already registered."

    except Exception as e:

        return False, str(e)

    finally:

        conn.close()


# ============================================================
# 9. USER LOGIN
# ============================================================

def login_user(email, password):

    email = email.strip().lower()

    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT email, password
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    conn.close()

    if row:

        if row["password"] == password:

            return True

    return False


# ============================================================
# 10. UPDATE PASSWORD
# ============================================================

def update_password(email, new_password):

    email = email.strip().lower()

    conn = get_db_connection()

    cursor = conn.execute(
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

    conn.commit()

    result = cursor.rowcount > 0


    conn.close()

    return result


# ============================================================
# 11. ACTIVITY LOGGING
# ============================================================

def log_activity(user_email, topic):

    try:

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO usage_logs
            (user_email, topic, timestamp)
            VALUES (?, ?, ?)
            """,
            (
                user_email,
                topic,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()

        conn.close()

    except Exception:

        pass


# ============================================================
# 12. ANALYTICS
# ============================================================

def get_analytics():

    conn = get_db_connection()

    total_users = conn.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    ).fetchone()[0]

    topic_data = pd.read_sql_query(
        """
        SELECT
            topic,
            COUNT(*) AS count
        FROM usage_logs
        GROUP BY topic
        ORDER BY count DESC
        """,
        conn
    )

    recent_data = pd.read_sql_query(
        """
        SELECT
            user_email,
            topic,
            timestamp
        FROM usage_logs
        ORDER BY id DESC
        LIMIT 100
        """,
        conn
    )

    conn.close()

    return (
        total_users,
        topic_data,
        recent_data
    )


# ============================================================
# 13. PASSWORD STRENGTH
# ============================================================

def password_strength(password):

    score = 0

    if len(password) >= 8:
        score += 1

    if re.search(
        r"[A-Z]",
        password
    ):
        score += 1

    if re.search(
        r"[a-z]",
        password
    ):
        score += 1

    if re.search(
        r"\d",
        password
    ):
        score += 1

    if re.search(
        r"[^A-Za-z0-9]",
        password
    ):
        score += 1

    if score <= 2:
        return "Weak"

    if score <= 4:
        return "Medium"

    return "Strong"


# ============================================================
# 14. GEMINI SYSTEM INSTRUCTION
# ============================================================

def build_system_instruction(topic="General"):

    language = st.session_state.get(
        "response_language",
        "Auto Detect"
    )

    style = st.session_state.get(
        "response_style",
        "Normal"
    )

    instructions = [

        "You are an Personal AI Chatbot.",

        "Answer the user's question naturally and accurately.",

        "Do not unnecessarily restrict normal general questions.",

        f"Current application topic: {topic}."

    ]

    if language == "English":

        instructions.append(
            "Respond in English."
        )

    elif language == "Tamil":

        instructions.append(
            "Respond primarily in Tamil."
        )

    elif language == "Tanglish":

        instructions.append(
            "Respond primarily in simple Tanglish."
        )

    if style == "Short":

        instructions.append(
            "Keep responses concise."
        )

    elif style == "Detailed":

        instructions.append(
            "Give detailed explanations and examples when useful."
        )

    elif style == "Simple":

        instructions.append(
            "Use simple beginner-friendly language."
        )

    return "\n".join(instructions)


# ============================================================
# 15. NORMAL GEMINI LLM
# ============================================================

def generate_ai_response(
    user_message,
    topic="General",
    extra_context="",
    allow_google_search=None
):

    if not client:

        return (
            "Gemini API key is not configured. "
            "Please check your .env file."
        )

    system_instruction = build_system_instruction(
        topic
    )

    if extra_context:

        system_instruction += (
            "\n\nDOCUMENT CONTEXT:\n"
            + extra_context[:50000]
        )

    try:

        config_kwargs = {

            "temperature": 0.7,

            "system_instruction":
                system_instruction

        }

        search_allowed = (
            st.session_state.get("google_search_enabled", True)
            if allow_google_search is None
            else allow_google_search
        )

        # Movies never use Google. Movie data comes only from MCP.
        if topic != "Movies" and search_allowed:

            config_kwargs["tools"] = [

                types.Tool(
                    google_search=types.GoogleSearch()
                )

            ]

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=user_message,

            config=types.GenerateContentConfig(
                **config_kwargs
            )

        )

        if response and response.text:

            return response.text

        return "I couldn't generate a response."

    except Exception as e:

        return (
            "Gemini Error:\n\n"
            + str(e)
        )


# ============================================================
# 16. IMAGE GENERATION
# ============================================================

def generate_image(prompt, aspect_ratio="1:1"):

    if not IMAGE_API_KEY:

        return (
            None,
            "IMAGE_API_KEY is not configured. "
            "Please add it to your .env file."
        )

    if not prompt.strip():

        return (
            None,
            "Please enter an image prompt."
        )

    # Output dimensions for the selected aspect ratio.
    dimensions = {
        "1:1": (1024, 1024),
        "16:9": (1344, 768),
        "9:16": (768, 1344),
        "4:3": (1152, 864)
    }

    width, height = dimensions.get(
        aspect_ratio,
        (1024, 1024)
    )

    try:

        from huggingface_hub import InferenceClient

        image_client = InferenceClient(
            provider="auto",
            api_key=IMAGE_API_KEY
        )

        # Hugging Face returns a PIL Image object.
        image = image_client.text_to_image(
            prompt=prompt,
            model=IMAGE_MODEL,
            width=width,
            height=height
        )

        if image is None:

            return (
                None,
                "Hugging Face did not return an image."
            )

        # Convert PIL image to PNG bytes so Streamlit
        # can display it and provide a download button.
        from io import BytesIO

        image_buffer = BytesIO()

        image.save(
            image_buffer,
            format="PNG"
        )

        image_bytes = image_buffer.getvalue()

        if not image_bytes:

            return (
                None,
                "Generated image is empty."
            )

        return (
            image_bytes,
            None
        )

    except ImportError:

        return (
            None,
            "huggingface_hub is not installed. "
            "Run: pip install -U huggingface_hub"
        )

    except Exception as e:

        return (
            None,
            "Hugging Face image generation error: "
            + str(e)
        )



# ============================================================
# 17. DOCUMENT PROCESSING
# ============================================================

def extract_pdf_text(uploaded_file):

    if PdfReader is None:

        return (
            "Install pypdf using: "
            "pip install pypdf"
        )

    try:

        uploaded_file.seek(0)

        reader = PdfReader(
            uploaded_file
        )

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:

                pages.append(text)

        return "\n\n".join(pages)

    except Exception as e:

        return (
            "PDF extraction error: "
            + str(e)
        )


def extract_excel_text(uploaded_file):

    try:

        uploaded_file.seek(0)

        excel_file = pd.ExcelFile(
            uploaded_file
        )

        all_text = []

        for sheet in excel_file.sheet_names:

            df = pd.read_excel(
                excel_file,
                sheet_name=sheet
            )

            all_text.append(
                "SHEET: "
                + sheet
                + "\n\n"
                + df.to_string(
                    index=False
                )
            )

        return "\n\n".join(
            all_text
        )

    except Exception as e:

        return (
            "Excel extraction error: "
            + str(e)
        )


def extract_csv_text(uploaded_file):

    try:

        uploaded_file.seek(0)

        df = pd.read_csv(
            uploaded_file
        )

        return df.to_string(
            index=False
        )

    except Exception as e:

        return (
            "CSV extraction error: "
            + str(e)
        )


def process_document(uploaded_file):

    filename = (
        uploaded_file.name
        .lower()
    )

    if filename.endswith(".pdf"):

        return extract_pdf_text(
            uploaded_file
        )

    if (
        filename.endswith(".xlsx")
        or filename.endswith(".xls")
    ):

        return extract_excel_text(
            uploaded_file
        )

    if filename.endswith(".csv"):

        return extract_csv_text(
            uploaded_file
        )

    return (
        "Unsupported document format."
    )


# ============================================================
# 18. MCP CONTROL PLANE
# ============================================================

DEFAULT_MCP_CONFIG = {
    "movies": {
        "name": "TMDB Movie MCP",
        "enabled": True,
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(TMDB_MCP_FILE)],
        "url": "",
        "env": {},
        "headers": {},
        "tools": ["search_movies", "get_movie_details", "get_movie_credits"]
    }
}

TMDB_MCP_SERVER_CODE = 'import json\nimport os\nfrom typing import Any\n\nimport requests\nfrom mcp.server import MCPServer\n\nTMDB_API_TOKEN = os.getenv("TMDB_API_TOKEN", "").strip()\nTMDB_BASE_URL = "https://api.themoviedb.org/3"\n\nmcp = MCPServer(\n    "TMDB Movie MCP",\n    instructions=(\n        "Use TMDB tools for movie discovery and details. "\n        "Search for a movie before requesting its details."\n    )\n)\n\n\ndef tmdb_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:\n    if not TMDB_API_TOKEN:\n        raise RuntimeError("TMDB_API_TOKEN is missing.")\n    headers = {"Authorization": f"Bearer {TMDB_API_TOKEN}", "accept": "application/json"}\n    response = requests.get(\n        f"{TMDB_BASE_URL}{path}",\n        headers=headers,\n        params=params or {},\n        timeout=20,\n    )\n    response.raise_for_status()\n    return response.json()\n\n\n@mcp.tool(title="Search movies")\ndef search_movies(query: str, language: str = "en-US", page: int = 1) -> str:\n    """Search TMDB for movies by title, translated title, or alternative title."""\n    query = query.strip()\n    if not query:\n        return json.dumps({"success": False, "message": "Movie query is required."})\n    data = tmdb_get(\n        "/search/movie",\n        {"query": query, "language": language, "page": max(1, min(page, 10)), "include_adult": "false"},\n    )\n    results = []\n    for item in data.get("results", [])[:8]:\n        results.append({\n            "id": item.get("id"),\n            "title": item.get("title"),\n            "original_title": item.get("original_title"),\n            "release_date": item.get("release_date"),\n            "overview": item.get("overview"),\n            "vote_average": item.get("vote_average"),\n            "vote_count": item.get("vote_count"),\n            "poster_path": item.get("poster_path"),\n            "backdrop_path": item.get("backdrop_path"),\n            "original_language": item.get("original_language"),\n        })\n    return json.dumps({"success": True, "query": query, "results": results}, ensure_ascii=False)\n\n\n@mcp.tool(title="Get movie details")\ndef get_movie_details(movie_id: int, language: str = "en-US") -> str:\n    """Get full TMDB details for a movie by its TMDB movie ID."""\n    data = tmdb_get(f"/movie/{int(movie_id)}", {"language": language, "append_to_response": "videos"})\n    result = {\n        "id": data.get("id"), "title": data.get("title"), "original_title": data.get("original_title"),\n        "tagline": data.get("tagline"), "overview": data.get("overview"), "release_date": data.get("release_date"),\n        "runtime": data.get("runtime"), "status": data.get("status"), "original_language": data.get("original_language"),\n        "genres": [g.get("name") for g in data.get("genres", [])], "vote_average": data.get("vote_average"),\n        "vote_count": data.get("vote_count"), "popularity": data.get("popularity"), "budget": data.get("budget"),\n        "revenue": data.get("revenue"), "homepage": data.get("homepage"), "poster_path": data.get("poster_path"),\n        "backdrop_path": data.get("backdrop_path"),\n        "production_companies": [c.get("name") for c in data.get("production_companies", [])],\n        "production_countries": [c.get("name") for c in data.get("production_countries", [])],\n    }\n    return json.dumps({"success": True, "movie": result}, ensure_ascii=False)\n\n\n@mcp.tool(title="Get movie credits")\ndef get_movie_credits(movie_id: int, language: str = "en-US") -> str:\n    """Get cast and crew information for a TMDB movie ID."""\n    data = tmdb_get(f"/movie/{int(movie_id)}/credits", {"language": language})\n    cast = [{"name": c.get("name"), "character": c.get("character"), "order": c.get("order")} for c in data.get("cast", [])[:15]]\n    crew = [\n        {"name": c.get("name"), "job": c.get("job"), "department": c.get("department")}\n        for c in data.get("crew", [])\n        if c.get("job") in {"Director", "Writer", "Screenplay", "Producer"}\n    ][:20]\n    return json.dumps({"success": True, "movie_id": movie_id, "cast": cast, "crew": crew}, ensure_ascii=False)\n\n\n@mcp.resource("tmdb://status")\ndef server_status() -> str:\n    """Current configuration status of the TMDB MCP server."""\n    return json.dumps({\n        "server": "TMDB Movie MCP",\n        "tmdb_token_configured": bool(TMDB_API_TOKEN),\n        "tools": ["search_movies", "get_movie_details", "get_movie_credits"],\n    })\n\n\n@mcp.prompt()\ndef movie_research(movie_name: str) -> str:\n    """Create a structured movie research prompt for an AI host."""\n    return (\n        f"Research the movie \'{movie_name}\' using the available TMDB tools. "\n        "Return title, release date, runtime, genres, rating, overview, key cast, director, and official homepage when available."\n    )\n\n\nif __name__ == "__main__":\n    mcp.run()\n'


def ensure_tmdb_mcp_server():
    try:
        if not TMDB_MCP_FILE.exists():
            TMDB_MCP_FILE.write_text(TMDB_MCP_SERVER_CODE, encoding="utf-8")
        return True
    except Exception:
        return False


def load_mcp_config():
    if not MCP_CONFIG_FILE.exists():
        config = json.loads(json.dumps(DEFAULT_MCP_CONFIG))
        try:
            MCP_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception:
            pass
        return config
    try:
        config = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("MCP configuration must be an object.")
        movies = config.get("movies")
        if not movies or "transport" not in movies:
            config["movies"] = json.loads(json.dumps(DEFAULT_MCP_CONFIG["movies"]))
        else:
            movies.setdefault("env", {})
            movies.setdefault("headers", {})
            movies.setdefault("url", "")
            movies.setdefault("tools", [])
        return config
    except Exception:
        return json.loads(json.dumps(DEFAULT_MCP_CONFIG))


if not st.session_state["mcp_servers"]:
    st.session_state["mcp_servers"] = load_mcp_config()


def save_mcp_config(config):
    try:
        MCP_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        st.session_state["mcp_servers"] = config
        return True
    except Exception:
        return False


def _json_safe(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _mcp_tool_summary(tool):
    return {
        "name": getattr(tool, "name", ""),
        "title": getattr(tool, "title", None),
        "description": getattr(tool, "description", None),
        "input_schema": _json_safe(getattr(tool, "inputSchema", None)),
    }


def _mcp_content_to_text(result):
    chunks = []
    for block in getattr(result, "content", []) or []:
        text_value = getattr(block, "text", None)
        if text_value:
            chunks.append(text_value)
    return "\n".join(chunks).strip()


async def _mcp_connect_and_action(config, action="list_tools", tool_name=None, arguments=None):
    from mcp import Client, StdioServerParameters

    transport = config.get("transport", "stdio")

    if transport == "stdio":
        env = {str(k): str(v) for k, v in (config.get("env") or {}).items()}
        # Inject TMDB secret at runtime; never persist it in mcp_servers.json.
        if config.get("name") == "TMDB Movie MCP" and TMDB_API_TOKEN:
            env["TMDB_API_TOKEN"] = TMDB_API_TOKEN
        server = StdioServerParameters(
            command=config.get("command") or sys.executable,
            args=config.get("args") or [],
            env=env,
        )
        async with Client(server) as client:
            if action == "list_tools":
                return await client.list_tools()
            if action == "call_tool":
                return await client.call_tool(tool_name, arguments or {})
            if action == "list_resources":
                return await client.list_resources()
            if action == "list_prompts":
                return await client.list_prompts()
            return None

    if transport == "streamable_http":
        url = (config.get("url") or "").strip()
        if not url:
            raise ValueError("Streamable HTTP MCP server URL is required.")
        headers = config.get("headers") or {}
        if headers:
            import httpx2
            from mcp.client.streamable_http import streamable_http_client
            async with httpx2.AsyncClient(
                headers={str(k): str(v) for k, v in headers.items()},
                timeout=httpx2.Timeout(30.0, read=300.0),
            ) as http_client:
                transport_obj = streamable_http_client(url, http_client=http_client)
                async with Client(transport_obj) as client:
                    if action == "list_tools":
                        return await client.list_tools()
                    if action == "call_tool":
                        return await client.call_tool(tool_name, arguments or {})
                    if action == "list_resources":
                        return await client.list_resources()
                    if action == "list_prompts":
                        return await client.list_prompts()
                    return None
        async with Client(url) as client:
            if action == "list_tools":
                return await client.list_tools()
            if action == "call_tool":
                return await client.call_tool(tool_name, arguments or {})
            if action == "list_resources":
                return await client.list_resources()
            if action == "list_prompts":
                return await client.list_prompts()
            return None

    raise ValueError("Unsupported MCP transport. Use stdio or streamable_http.")


def run_mcp_action(config, action="list_tools", tool_name=None, arguments=None):
    return asyncio.run(_mcp_connect_and_action(config, action, tool_name, arguments))


def discover_mcp_tools(server_name):
    config = st.session_state["mcp_servers"].get(server_name)
    if not config:
        return False, "MCP server not found.", []
    if not config.get("enabled", True):
        return False, "MCP server is disabled.", []
    try:
        result = run_mcp_action(config, "list_tools")
        tools = [_mcp_tool_summary(t) for t in getattr(result, "tools", [])]
        config["tools"] = [t["name"] for t in tools]
        save_mcp_config(st.session_state["mcp_servers"])
        return True, f"Discovered {len(tools)} tool(s).", tools
    except Exception as e:
        return False, f"MCP discovery failed: {e}", []


def test_mcp_server(server_name):
    config = st.session_state["mcp_servers"].get(server_name)
    if not config:
        return False, "Server not found."
    if not config.get("enabled", True):
        return False, "Server is disabled."
    try:
        result = run_mcp_action(config, "list_tools")
        names = [getattr(t, "name", "") for t in getattr(result, "tools", [])]
        config["tools"] = [n for n in names if n]
        save_mcp_config(st.session_state["mcp_servers"])
        return True, f"Connected successfully • {len(names)} tool(s): {', '.join(names) if names else 'none'}"
    except Exception as e:
        return False, f"Connection failed: {e}"


def call_mcp_tool(server_name, tool_name, arguments=None):
    config = st.session_state["mcp_servers"].get(server_name)
    if not config or not config.get("enabled", True):
        return None, "MCP server is unavailable or disabled."
    try:
        result = run_mcp_action(config, "call_tool", tool_name, arguments or {})
        if getattr(result, "is_error", False):
            return None, _mcp_content_to_text(result) or "MCP tool returned an error."
        return result, None
    except Exception as e:
        return None, str(e)


def _parse_mcp_json_result(result):
    text = _mcp_content_to_text(result)
    if not text:
        structured = getattr(result, "structured_content", None)
        return structured if isinstance(structured, dict) else None
    try:
        return json.loads(text)
    except Exception:
        structured = getattr(result, "structured_content", None)
        return structured if isinstance(structured, dict) else {"success": True, "text": text}


def extract_movie_query(user_prompt):
    """Extract a clean movie title from common natural-language movie questions."""
    query = user_prompt.strip()
    query = re.sub(
        r"\b(what is|what's|who is|who's|tell me|give me|show me|can you tell me|details of|details about|information about|info about|about|movie|film|cast of|cast|hero of|heroine of|hero|heroine|actor of|actress of|director of|director|rating of|rating|review of|review|story of|story|plot of|plot|release date of|release date|when did|when was|is|the|a|an|of)\b",
        " ", query, flags=re.IGNORECASE
    )
    query = re.sub(r"[?!.:,;]+", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query or user_prompt.strip()


def movie_mcp_lookup(user_prompt):
    movie_query = extract_movie_query(user_prompt)
    search_result, search_error = call_mcp_tool(
        "movies", "search_movies", {"query": movie_query, "language": "en-US", "page": 1}
    )
    if search_error:
        return None, search_error
    search_data = _parse_mcp_json_result(search_result) or {}
    matches = search_data.get("results", [])
    if not matches:
        return None, f"No TMDB movie match found for '{movie_query}'."
    movie_id = matches[0].get("id")
    if not movie_id:
        return None, "TMDB returned a movie without an ID."
    details_result, details_error = call_mcp_tool(
        "movies", "get_movie_details", {"movie_id": int(movie_id), "language": "en-US"}
    )
    if details_error:
        return None, details_error
    details_data = _parse_mcp_json_result(details_result) or {}
    credits_result, credits_error = call_mcp_tool(
        "movies", "get_movie_credits", {"movie_id": int(movie_id), "language": "en-US"}
    )
    credits_data = _parse_mcp_json_result(credits_result) if not credits_error and credits_result else {}
    return {"query": movie_query, "movie": details_data.get("movie", details_data), "credits": credits_data or {}}, None


ensure_tmdb_mcp_server()


# ============================================================
# 25. PAGE NAVIGATION
# ============================================================

def go_to_page(page_name):

    st.session_state[
        "current_page"
    ] = page_name

    try:

        st.query_params[
            "page"
        ] = page_name

    except Exception:

        pass

    st.rerun()


def get_current_page():

    try:

        page = st.query_params.get(
            "page"
        )

        if page:

            return page

    except Exception:

        pass

    return st.session_state.get(
        "current_page",
        "general"
    )


# ============================================================
# 26. LOGOUT
# ============================================================

def logout():

    st.session_state[
        "logged_in"
    ] = False

    st.session_state[
        "user_email"
    ] = None

    st.session_state[
        "is_admin"
    ] = False

    st.session_state[
        "current_page"
    ] = "general"

    st.session_state[
        "google_oauth_state"
    ] = None

    try:

        st.query_params.clear()

    except Exception:

        pass

    st.rerun()


# ============================================================
# 27. GOOGLE OAUTH - CREATE AUTH URL
# ============================================================

def create_google_auth_url():

    # Use a signed state value instead of relying only on Streamlit
    # session state. OAuth redirects can create a fresh Streamlit run/session,
    # which can otherwise cause a false "state mismatch" error.
    oauth_secret = os.getenv(
        "OAUTH_STATE_SECRET",
        GOOGLE_CLIENT_SECRET or "local-dev-oauth-state-secret"
    ).strip()

    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(32)
    payload = timestamp + "." + nonce
    signature = hmac.new(
        oauth_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    state = payload + "." + signature

    # Keep it in session too, but callback validation does not depend on it.
    st.session_state[
        "google_oauth_state"
    ] = state

    params = {

        "client_id":
            GOOGLE_CLIENT_ID,

        "redirect_uri":
            GOOGLE_REDIRECT_URI,

        "response_type":
            "code",

        "scope":
            "openid email profile",

        "state":
            state,

        "access_type":
            "offline",

        "prompt":
            "select_account"

    }

    return (
        "https://accounts.google.com/"
        "o/oauth2/v2/auth?"
        + urlencode(params)
    )


# ============================================================
# 28. GOOGLE OAUTH - CALLBACK
# ============================================================

def handle_google_callback():

    try:

        code = st.query_params.get(
            "code"
        )

        returned_state = (
            st.query_params.get(
                "state"
            )
        )

        error = st.query_params.get(
            "error"
        )

        # No Google callback
        if not code and not error:

            return False

        # Google login cancelled
        if error:

            st.error(
                "Google login was cancelled."
            )

            st.query_params.clear()

            return False

        # ----------------------------------------------------
        # VERIFY SIGNED OAUTH STATE
        # ----------------------------------------------------
        # Do not depend only on st.session_state here. After Google
        # redirects back to Streamlit, the app may be running in a new
        # session, which was causing the false state-mismatch error.
        oauth_secret = os.getenv(
            "OAUTH_STATE_SECRET",
            GOOGLE_CLIENT_SECRET or "local-dev-oauth-state-secret"
        ).strip()

        state_valid = False

        if returned_state:
            try:
                parts = returned_state.split(".", 2)

                if len(parts) == 3:
                    timestamp, nonce, signature = parts
                    payload = timestamp + "." + nonce

                    expected_signature = hmac.new(
                        oauth_secret.encode("utf-8"),
                        payload.encode("utf-8"),
                        hashlib.sha256
                    ).hexdigest()

                    age = int(time.time()) - int(timestamp)

                    state_valid = (
                        hmac.compare_digest(
                            signature,
                            expected_signature
                        )
                        and 0 <= age <= 600
                    )
            except Exception:
                state_valid = False

        if not state_valid:

            st.error(
                "Google authentication state mismatch or expired. "
                "Please click Continue with Google again."
            )

            st.query_params.clear()

            st.session_state[
                "google_oauth_state"
            ] = None

            return False

        # ----------------------------------------------------
        # EXCHANGE CODE FOR TOKEN
        # ----------------------------------------------------

        token_response = requests.post(

            "https://oauth2.googleapis.com/token",

            data={

                "code":
                    code,

                "client_id":
                    GOOGLE_CLIENT_ID,

                "client_secret":
                    GOOGLE_CLIENT_SECRET,

                "redirect_uri":
                    GOOGLE_REDIRECT_URI,

                "grant_type":
                    "authorization_code"

            },

            timeout=10

        )

        if token_response.status_code != 200:

            st.error(
                "Google token exchange failed."
            )

            st.query_params.clear()

            return False

        token_data = (
            token_response.json()
        )

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            st.error(
                "Google access token was not received."
            )

            st.query_params.clear()

            return False

        # ----------------------------------------------------
        # GET GOOGLE USER INFO
        # ----------------------------------------------------

        user_response = requests.get(

            "https://www.googleapis.com/oauth2/v2/userinfo",

            headers={
                "Authorization":
                    "Bearer "
                    + access_token
            },

            timeout=10

        )

        if user_response.status_code != 200:

            st.error(
                "Could not get Google account information."
            )

            st.query_params.clear()

            return False

        google_user = (
            user_response.json()
        )

        email = (
            google_user
            .get("email", "")
            .strip()
            .lower()
        )

        if not email:

            st.error(
                "Google email was not received."
            )

            st.query_params.clear()

            return False

        # ----------------------------------------------------
        # CREATE USER IF NOT EXISTS
        # ----------------------------------------------------

        conn = get_db_connection()

        existing = conn.execute(
            """
            SELECT email
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if not existing:

            random_password = (
                secrets.token_urlsafe(
                    32
                )
            )

            conn.execute(
                """
                INSERT INTO users
                (email, password)
                VALUES (?, ?)
                """,
                (
                    email,
                    random_password
                )
            )

            conn.commit()

        conn.close()

        # ----------------------------------------------------
        # LOGIN USER
        # ----------------------------------------------------

        st.session_state[
            "logged_in"
        ] = True

        st.session_state[
            "user_email"
        ] = email

        st.session_state[
            "is_admin"
        ] = (
            email.lower()
            == ADMIN_USERNAME.lower()
        )

        st.session_state[
            "current_page"
        ] = (
            "admin"
            if st.session_state[
                "is_admin"
            ]
            else "general"
        )

        st.session_state[
            "google_oauth_state"
        ] = None

        # Remove OAuth query parameters
        st.query_params.clear()

        return True

    except Exception as e:

        st.error(
            "Google Login Error: "
            + str(e)
        )

        try:

            st.query_params.clear()

        except Exception:

            pass

        return False


# ============================================================
# 29. GOOGLE LOGIN BUTTON
# ============================================================

def render_google_login():

    if not GOOGLE_CLIENT_ID:

        st.warning(
            "Google OAuth is not configured."
        )

        return

    auth_url = (
        create_google_auth_url()
    )

    st.link_button(

        "🔵 Continue with Google",

        auth_url,

        use_container_width=True

    )


# ============================================================
# 30. LOGIN PAGE
# ============================================================

def render_login_page():

    st.markdown(
        """
        <div class="main-title">
            🤖 Personal AI Chatbot
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sub-title">
            Gemini AI • Movies • Image Generation • Document Chat
        </div>
        """,
        unsafe_allow_html=True
    )

    login_tab, signup_tab, forgot_tab = st.tabs(
        [
            "🔐 Login",
            "📝 Signup",
            "🔑 Forgot Password"
        ]
    )

    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        with st.form(
            "login_form"
        ):

            email = st.text_input(
                "Email",
                placeholder="Enter your email"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            login_submit = st.form_submit_button(
                "🔐 Login",
                type="primary",
                use_container_width=True
            )

        if login_submit:

            email = email.strip().lower()

            if not email or not password:

                st.error(
                    "Please enter email and password."
                )

            elif (
                email
                == ADMIN_USERNAME.lower()
                and password
                == ADMIN_PASSWORD
            ):

                st.session_state[
                    "logged_in"
                ] = True

                st.session_state[
                    "user_email"
                ] = email

                st.session_state[
                    "is_admin"
                ] = True

                st.session_state[
                    "current_page"
                ] = "admin"

                st.rerun()

            elif login_user(
                email,
                password
            ):

                st.session_state[
                    "logged_in"
                ] = True

                st.session_state[
                    "user_email"
                ] = email

                st.session_state[
                    "is_admin"
                ] = False

                st.session_state[
                    "current_page"
                ] = "general"

                st.rerun()

            else:

                st.error(
                    "❌ Invalid email or password."
                )

        st.divider()

        st.markdown(
            "<center>OR</center>",
            unsafe_allow_html=True
        )

        st.write("")

        render_google_login()

    # ========================================================
    # SIGNUP
    # ========================================================

    with signup_tab:

        with st.form(
            "signup_form"
        ):

            email = st.text_input(
                "Email",
                placeholder="Enter email"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm = st.text_input(
                "Confirm Password",
                type="password"
            )

            signup_submit = st.form_submit_button(
                "📝 Create Account",
                use_container_width=True
            )

        if signup_submit:

            if not email or not password:

                st.error(
                    "All fields are required."
                )

            elif password != confirm:

                st.error(
                    "Passwords do not match."
                )

            elif len(password) < 6:

                st.error(
                    "Password must contain at least 6 characters."
                )

            else:

                success, message = register_user(
                    email,
                    password
                )

                if success:

                    st.success(
                        "✅ Account created successfully."
                    )

                else:

                    st.error(message)

    # ========================================================
    # FORGOT PASSWORD
    # ========================================================

    with forgot_tab:

        with st.form(
            "forgot_form"
        ):

            email = st.text_input(
                "Registered Email"
            )

            new_password = st.text_input(
                "New Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            reset_submit = st.form_submit_button(
                "🔑 Reset Password",
                use_container_width=True
            )

        if reset_submit:

            if new_password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            elif len(new_password) < 6:

                st.error(
                    "Password must contain at least 6 characters."
                )

            elif update_password(
                email,
                new_password
            ):

                st.success(
                    "Password updated successfully."
                )

            else:

                st.error(
                    "Email not found."
                )


# ============================================================
# 31. GENERAL PAGE
# ============================================================

def render_general_page():

    st.title("💬 General")

    st.caption(
        "Normal LLM chatbot — ask anything."
    )

    messages = st.session_state[
        "general_messages"
    ]

    for message in messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

            if (
                st.session_state[
                    "show_timestamps"
                ]
                and message.get(
                    "timestamp"
                )
            ):

                st.caption(
                    message["timestamp"]
                )

    prompt = st.chat_input(
        "Message AI..."
    )

    if prompt:

        timestamp = datetime.now().strftime(
            "%H:%M"
        )

        messages.append({

            "role":
                "user",

            "content":
                prompt,

            "timestamp":
                timestamp

        })

        log_activity(
            st.session_state[
                "user_email"
            ],
            "General"
        )

        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Thinking..."
            ):

                response = (
                    generate_ai_response(
                        prompt,
                        "General"
                    )
                )

            st.markdown(
                response
            )

        messages.append({

            "role":
                "assistant",

            "content":
                response,

            "timestamp":
                timestamp

        })


# ============================================================
# 32. MOVIES PAGE
# ============================================================

def render_movies_page():

    st.title("🎬 Movies")
    st.caption("Ask about any movie — title, cast, hero, heroine, director, rating, story, release date and more.")

    messages = st.session_state["movie_messages"]

    for message in messages:
        with st.chat_message(message["role"]):
            if message.get("poster"):
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.image(message["poster"], use_container_width=True)
                with c2:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])

    prompt = st.chat_input("Ask about any movie...")

    if prompt:
        messages.append({"role": "user", "content": prompt})
        log_activity(st.session_state["user_email"], "Movies")

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🎬 Getting movie details..."):
                movie_data, error = movie_mcp_lookup(prompt)

                if error:
                    # No Google search and no MCP/debug text is shown to the user.
                    response = (
                        "### 🎬 Movie details unavailable\n\n"
                        f"I couldn't find reliable details for **{extract_movie_query(prompt)}** right now. "
                        "Please check the movie title and try again."
                    )
                    poster_url = None
                else:
                    movie = movie_data["movie"]
                    credits = movie_data.get("credits", {})
                    cast = credits.get("cast", [])
                    crew = credits.get("crew", [])
                    director = next(
                        (x.get("name") for x in crew if x.get("job") == "Director"),
                        "Not available",
                    )
                    cast_text = ", ".join(
                        x.get("name", "") for x in cast[:10] if x.get("name")
                    ) or "Not available"

                    title = movie.get("title") or movie_data.get("query") or "Movie"
                    release = movie.get("release_date") or "N/A"
                    rating = movie.get("vote_average")
                    rating_text = f"{float(rating):.1f}/10" if isinstance(rating, (int, float)) else "N/A"
                    genres = ", ".join(movie.get("genres", [])) or "N/A"
                    runtime = movie.get("runtime")
                    runtime_text = f"{runtime} minutes" if runtime else "N/A"
                    overview = movie.get("overview") or "No overview available."
                    poster_path = movie.get("poster_path")
                    poster_url = (
                        f"https://image.tmdb.org/t/p/w500{poster_path}"
                        if poster_path else None
                    )

                    response = (
                        f"### 🎬 {title}\n\n"
                        f"**Release Date:** {release}  \n"
                        f"**Rating:** {rating_text}  \n"
                        f"**Runtime:** {runtime_text}  \n"
                        f"**Genres:** {genres}\n\n"
                        f"**Director:** {director}\n\n"
                        f"**Cast:** {cast_text}\n\n"
                        f"**Story / Overview:** {overview}"
                    )

            st.markdown(response)

        messages.append({
            "role": "assistant",
            "content": response,
            "poster": poster_url,
        })


# ============================================================
# 33. CREATE IMAGE PAGE
# ============================================================

def render_image_page():

    st.title("🎨 Create Image")

    st.caption(
        "Give a command describing the image you want. "
        "Images are generated using the separate Hugging Face API."
    )

    st.info(
        "Example: "
        "Create an image of a futuristic city "
        "with flying cars at night."
    )

    messages = st.session_state[
        "image_messages"
    ]

    for message in messages:

        if message["role"] == "user":

            with st.chat_message(
                "user"
            ):

                st.markdown(
                    message["content"]
                )

        elif message["role"] == "assistant":

            with st.chat_message(
                "assistant"
            ):

                if message.get(
                    "image"
                ):

                    st.image(
                        message["image"],
                        use_container_width=True
                    )

                if message.get(
                    "text"
                ):

                    st.markdown(
                        message["text"]
                    )

    prompt = st.text_area(
        "Image Command",
        placeholder=(
            "Create an image of a futuristic "
            "city with neon lights, flying cars "
            "and a cinematic night atmosphere."
        ),
        height=130
    )

    col1, col2 = st.columns(2)

    with col1:

        aspect_ratio = st.selectbox(
            "Aspect Ratio",
            [
                "1:1",
                "16:9",
                "9:16",
                "4:3"
            ]
        )

    with col2:

        style = st.selectbox(
            "Style",
            [
                "Natural",
                "Photorealistic",
                "Cinematic",
                "Anime",
                "Digital Art",
                "3D",
                "Illustration"
            ]
        )

    if st.button(
        "🎨 Create Image",
        type="primary",
        use_container_width=True
    ):

        if not prompt.strip():

            st.warning(
                "Please enter an image command."
            )

            return

        final_prompt = f"""
Create an image based on the user's request.

USER REQUEST:
{prompt}

STYLE:
{style}

ASPECT RATIO:
{aspect_ratio}

Generate a high-quality image and follow
the user's description as closely as possible.
"""

        log_activity(
            st.session_state[
                "user_email"
            ],
            "Create Image"
        )

        with st.spinner(
            "🎨 Creating image..."
        ):

            image_bytes, error = (
                generate_image(
                    final_prompt,
                    aspect_ratio
                )
            )

        if error:

            st.error(
                error
            )

        else:

            st.success(
                "✅ Image created successfully!"
            )

            st.image(
                image_bytes,
                caption="Generated Image",
                use_container_width=True
            )

            st.download_button(

                "⬇️ Download Image",

                data=image_bytes,

                file_name="generated_image.png",

                mime="image/png",

                use_container_width=True

            )

            messages.append({

                "role":
                    "user",

                "content":
                    prompt

            })

            messages.append({

                "role":
                    "assistant",

                "image":
                    image_bytes,

                "text":
                    "Image generated successfully."

            })


# ============================================================
# 34. DOCUMENT CHAT PAGE
# ============================================================

def render_document_page():

    st.title("📄 Document Chat")

    st.caption(
        "Chat with PDF, Excel and CSV files."
    )

    uploaded_file = st.file_uploader(

        "Upload Document",

        type=[
            "pdf",
            "xlsx",
            "xls",
            "csv"
        ]

    )

    if uploaded_file:

        if (
            st.session_state[
                "uploaded_document_name"
            ]
            != uploaded_file.name
        ):

            with st.spinner(
                "Reading document..."
            ):

                document_text = (
                    process_document(
                        uploaded_file
                    )
                )

            st.session_state[
                "uploaded_document_name"
            ] = uploaded_file.name

            st.session_state[
                "uploaded_document_text"
            ] = document_text

            st.session_state[
                "document_messages"
            ] = []

            st.success(
                "Document loaded successfully."
            )

    if st.session_state[
        "uploaded_document_name"
    ]:

        st.info(
            "Current document: "
            + st.session_state[
                "uploaded_document_name"
            ]
        )

    messages = st.session_state[
        "document_messages"
    ]

    for message in messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    prompt = st.chat_input(
        "Ask something about your document..."
    )

    if prompt:

        if not st.session_state[
            "uploaded_document_text"
        ]:

            st.warning(
                "Please upload a document first."
            )

            return

        messages.append({

            "role":
                "user",

            "content":
                prompt

        })

        log_activity(
            st.session_state[
                "user_email"
            ],
            "Document Chat"
        )

        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Searching document..."
            ):

                response = (
                    generate_ai_response(

                        prompt,

                        "Document Chat",

                        st.session_state[
                            "uploaded_document_text"
                        ]

                    )
                )

            st.markdown(
                response
            )

        messages.append({

            "role":
                "assistant",

            "content":
                response

        })


# ============================================================
# 35. SETTINGS PAGE
# ============================================================

def render_settings_page():

    st.title("⚙️ Settings")
    st.caption("Application, chat and production-style MCP configuration.")

    st.subheader("💬 Chat Settings")
    languages = ["Auto Detect", "English", "Tamil", "Tanglish"]
    styles = ["Normal", "Short", "Detailed", "Simple"]

    language = st.selectbox("Response Language", languages, index=languages.index(st.session_state["response_language"]))
    response_style = st.selectbox("Response Style", styles, index=styles.index(st.session_state["response_style"]))
    show_timestamps = st.toggle("Show timestamps", value=st.session_state["show_timestamps"])
    google_search = st.toggle(
        "Google Search for General / Document Chat",
        value=st.session_state["google_search_enabled"],
    )
    st.session_state["response_language"] = language
    st.session_state["response_style"] = response_style
    st.session_state["show_timestamps"] = show_timestamps
    st.session_state["google_search_enabled"] = google_search

    st.divider()
    st.subheader("🔌 MCP Control Center")
    st.caption(
        "Connect, test and discover tools from MCP servers using the official MCP Python SDK. "
        "Supports local stdio and remote Streamable HTTP servers."
    )

    config = st.session_state["mcp_servers"]

    for server_name in list(config.keys()):
        server = config[server_name]
        st.markdown('<div class="mcp-card">', unsafe_allow_html=True)
        st.markdown(
            f"### 🔹 {server.get('name', server_name)}  `{'Enabled' if server.get('enabled', True) else 'Disabled'}`"
        )

        enabled = st.toggle(
            "Enable MCP Server",
            value=server.get("enabled", True),
            key=f"mcp_enabled_{server_name}",
        )
        server["enabled"] = enabled
        transport = server.get("transport", "stdio")
        st.write(f"**Transport:** `{transport}`")
        if transport == "stdio":
            st.write(f"**Command:** `{server.get('command', '')}`")
            st.write(f"**Arguments:** `{server.get('args', [])}`")
        else:
            st.write(f"**URL:** `{server.get('url', '')}`")

        tools = server.get("tools", [])
        st.write("**Discovered Tools:** " + (", ".join(tools) if tools else "Not discovered yet"))

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧪 Test Connection", key=f"mcp_test_{server_name}", use_container_width=True):
                with st.spinner("Testing MCP connection..."):
                    success, message = test_mcp_server(server_name)
                (st.success if success else st.error)(message)
        with c2:
            if st.button("🔎 Discover Tools", key=f"mcp_discover_{server_name}", use_container_width=True):
                with st.spinner("Discovering tools..."):
                    success, message, tools_info = discover_mcp_tools(server_name)
                if success:
                    st.success(message)
                    for tool in tools_info:
                        with st.expander(f"🛠️ {tool.get('name', 'tool')}"):
                            st.write(tool.get("description") or "No description")
                            st.json(tool.get("input_schema") or {})
                else:
                    st.error(message)
        with c3:
            if st.button("🗑️ Remove", key=f"mcp_delete_{server_name}", use_container_width=True):
                del config[server_name]
                save_mcp_config(config)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("➕ Add MCP Server")
    st.caption("Generic MCP host configuration: stdio or Streamable HTTP.")

    with st.form("add_mcp_server_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_id = st.text_input("Server ID", placeholder="github_mcp")
            new_name = st.text_input("Server Name", placeholder="GitHub MCP")
            new_transport = st.selectbox("Transport", ["stdio", "streamable_http"])
        with c2:
            new_command = st.text_input("Command (stdio)", value=sys.executable)
            new_args = st.text_input("Arguments (stdio, comma separated)", placeholder="server.py")
            new_url = st.text_input("URL (Streamable HTTP)", placeholder="http://127.0.0.1:8000/mcp")

        new_env = st.text_area("Environment JSON (optional)", value="{}", help='Example: {"API_KEY":"your-secret"}')
        new_headers = st.text_area("HTTP Headers JSON (optional)", value="{}", help='Example: {"Authorization":"Bearer your-token"}')
        add_server = st.form_submit_button("➕ Add MCP Server", use_container_width=True)

    if add_server:
        if not new_id.strip():
            st.error("Server ID is required.")
        elif new_id in config:
            st.error("Server already exists.")
        else:
            try:
                env_data = json.loads(new_env or "{}")
                headers_data = json.loads(new_headers or "{}")
                if not isinstance(env_data, dict) or not isinstance(headers_data, dict):
                    raise ValueError("Environment and headers must be JSON objects.")
                args = [x.strip() for x in new_args.split(",") if x.strip()]
                config[new_id] = {
                    "name": new_name.strip() or new_id,
                    "enabled": True,
                    "transport": new_transport,
                    "command": new_command.strip() or sys.executable,
                    "args": args,
                    "url": new_url.strip(),
                    "env": env_data,
                    "headers": headers_data,
                    "tools": [],
                }
                if save_mcp_config(config):
                    st.success("MCP server added.")
                    st.rerun()
            except Exception as e:
                st.error(f"Invalid MCP configuration: {e}")

    st.divider()
    st.subheader("🎬 TMDB Movie MCP")
    if TMDB_API_TOKEN:
        st.success("TMDB API token is configured.")
    else:
        st.warning("TMDB_API_TOKEN is not configured. Add it to .env before testing the Movie MCP.")
    st.code("TMDB_API_TOKEN=your_tmdb_api_read_access_token", language="bash")

    if st.button("💾 Save MCP Settings", use_container_width=True):
        if save_mcp_config(config):
            st.success("MCP settings saved.")

    st.divider()
    st.subheader("🧹 Chat Data")
    if st.button("Clear All Chat History", use_container_width=True):
        st.session_state["general_messages"] = []
        st.session_state["movie_messages"] = []
        st.session_state["image_messages"] = []
        st.session_state["document_messages"] = []
        st.success("Chat history cleared.")
    if st.button("Clear Uploaded Document", use_container_width=True):
        st.session_state["uploaded_document_name"] = None
        st.session_state["uploaded_document_text"] = ""
        st.session_state["document_messages"] = []
        st.success("Document cleared.")

    st.divider()
    st.subheader("ℹ️ App Information")
    st.write("**LLM:** Gemini 2.5 Flash")
    st.write("**Image Generation:** Hugging Face Inference API")
    st.write("**Movies:** TMDB through MCP")
    st.write("**MCP:** Official MCP Python SDK")
    st.write("**Database:** SQLite")
    st.write("**Framework:** Streamlit")
    st.write("**Language:** Python")


# ============================================================
# 36. ADMIN DASHBOARD
# ============================================================

def render_admin_dashboard():

    st.title(
        "📊 Admin Dashboard"
    )

    (
        total_users,
        topic_data,
        recent_data
    ) = get_analytics()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Users",
            total_users
        )

    with col2:

        total_requests = (

            int(
                topic_data[
                    "count"
                ].sum()
            )

            if not topic_data.empty

            else 0

        )

        st.metric(
            "Total Requests",
            total_requests
        )

    with col3:

        topics = len(
            topic_data
        )

        st.metric(
            "Topics Used",
            topics
        )

    st.divider()

    st.subheader(
        "📈 Topic Usage"
    )

    if not topic_data.empty:

        st.bar_chart(

            topic_data.set_index(
                "topic"
            )["count"]

        )

    else:

        st.info(
            "No topic usage data."
        )

    st.subheader(
        "🕒 Recent Activity"
    )

    if not recent_data.empty:

        st.dataframe(

            recent_data,

            use_container_width=True,

            hide_index=True

        )

    else:

        st.info(
            "No activity yet."
        )


# ============================================================
# 37. SIDEBAR
# ============================================================

def render_sidebar():

    with st.sidebar:

        st.markdown(
            "## 🤖 Personal AI Chatbot"
        )

        st.caption(
            st.session_state[
                "user_email"
            ]
        )

        st.divider()

        # ====================================================
        # CHAT CATEGORIES
        # ====================================================

        st.markdown(
            "### 📚 Chat Categories"
        )

        pages = [

            (
                "💬 General",
                "general"
            ),

            (
                "🎬 Movies",
                "movies"
            ),

            (
                "🎨 Create Image",
                "image"
            ),

            (
                "📄 Document Chat",
                "document"
            )

        ]

        for label, page in pages:

            if st.button(

                label,

                key=
                    f"navigation_{page}",

                use_container_width=True

            ):

                go_to_page(
                    page
                )

        st.divider()

        # ====================================================
        # SETTINGS
        # ====================================================

        if st.button(

            "⚙️ Settings",

            use_container_width=True

        ):

            go_to_page(
                "settings"
            )

        # ====================================================
        # ADMIN
        # ====================================================

        if st.session_state[
            "is_admin"
        ]:

            st.divider()

            st.markdown(
                "### 👑 Admin"
            )

            if st.button(

                "📊 Admin Dashboard",

                use_container_width=True

            ):

                go_to_page(
                    "admin"
                )

        st.divider()

        # ====================================================
        # LOGOUT
        # ====================================================

        if st.button(

            "🚪 Logout",

            use_container_width=True

        ):

            logout()


# ============================================================
# 38. PAGE ROUTER
# ============================================================

def render_application():

    render_sidebar()

    page = get_current_page()

    if page == "general":

        render_general_page()

    elif page == "movies":

        render_movies_page()

    elif page == "image":

        render_image_page()

    elif page == "document":

        render_document_page()

    elif page == "settings":

        render_settings_page()

    elif page == "admin":

        if st.session_state[
            "is_admin"
        ]:

            render_admin_dashboard()

        else:

            st.error(
                "Admin access required."
            )

    else:

        render_general_page()


# ============================================================
# 39. MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # GOOGLE OAUTH CALLBACK
    # --------------------------------------------------------

    if not st.session_state[
        "logged_in"
    ]:

        if GOOGLE_CLIENT_ID:

            oauth_success = (
                handle_google_callback()
            )

            if oauth_success:

                st.rerun()

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not st.session_state[
        "logged_in"
    ]:

        render_login_page()

        return

    # --------------------------------------------------------
    # APPLICATION
    # --------------------------------------------------------

    render_application()


# ============================================================
# 40. START APPLICATION
# ============================================================

if __name__ == "__main__":

    main()