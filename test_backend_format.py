import requests
import json

url = "http://127.0.0.1:8000/chat"
payload = {"question": "Which products have the highest number of billing documents?"}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)
print(json.dumps(response.json(), indent=2))
