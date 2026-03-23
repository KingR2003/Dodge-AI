import httpx
import os
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
resp = httpx.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]})
print(resp.status_code)
print(resp.text)
