#!/usr/bin/env python3
import requests
import json

API_URL = "http://localhost:8990"

print("🧪 Testando conexão com API...")

try:
    print(f"📡 Fazendo requisição para {API_URL}/api/sessions")
    response = requests.get(f"{API_URL}/api/sessions", timeout=5)
    
    print(f"📊 Status Code: {response.status_code}")
    print(f"📝 Headers: {dict(response.headers)}")
    print(f"📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"📏 Content-Length: {len(response.text)}")
    print(f"🔤 Raw Text: '{response.text}'")
    
    if response.status_code == 200:
        try:
            json_data = response.json()
            print(f"✅ JSON Parse: OK - {json_data}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
    
except Exception as e:
    print(f"❌ Connection Error: {e}")

print("\n🔍 Testando health endpoint...")
try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    print(f"📊 Health Status: {response.status_code}")
    print(f"📄 Health Response: {response.text}")
except Exception as e:
    print(f"❌ Health Error: {e}")