import httpx
import os
from dotenv import load_dotenv

# API Key load pandrom
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ API Key kidaikkala! .env file-a check pannunga.")
else:
    # Key update aagirukka nu check panna kadaisi 4 letters-a print pandrom
    print(f"✅ API Key Load Aagiduchu! (Key ends with: ...{api_key[-4:]})")
    
    # Google kitta direct-a model list kekkurom
    print("⏳ Google server-kitta check pandrom... Wait pannunga...\n")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    response = httpx.get(url, timeout=30.0)

    if response.status_code == 200:
        models = response.json().get("models", [])
        print("🔥 UNGA API KEY-KKU WORK AAGURA MODELS LIST 🔥")
        print("-" * 40)
        for m in models:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print(m["name"])
        print("-" * 40)
        print("Mela irukkura list-la endha peru varudho, adhu thaan namma code-la podanum!")
    else:
        print("❌ Google Server Error:")
        print(response.text)