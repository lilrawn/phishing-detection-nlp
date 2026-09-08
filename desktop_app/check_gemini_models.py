import os
import requests

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    raise SystemExit("Set the GEMINI_API_KEY environment variable before running this script.")
url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {'x-goog-api-key': api_key}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json()
        print("Available Gemini models:")
        for model in models.get('models', []):
            print(f"  • {model['name']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
