import httpx
import os
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
resp = httpx.get(url)
print(resp.status_code)
data = resp.json()
for m in data.get("models", []):
    if "generateContent" in m.get("supportedGenerationMethods", []):
        print(m["name"])
