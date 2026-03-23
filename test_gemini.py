import os

import httpx
from dotenv import load_dotenv


def main() -> None:
    # Load GEMINI_API_KEY from d:\Dodge AI\.env
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it to d:\\Dodge AI\\.env")

    model = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    print("key_loaded:", True)
    print("model:", model)

    # Minimal payload first (Gemini sometimes rejects extra fields depending on version).
    payload = {"contents": [{"parts": [{"text": "Say hello"}]}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    import requests
    resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=20.0)
    print("status:", resp.status_code)
    if resp.status_code >= 400:
        print("error_body:", resp.text)
        return

    data = resp.json()

    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    print(text)


if __name__ == "__main__":
    main()

