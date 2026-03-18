# Save as check_gemini_models.py
import requests

api_key = "AIzaSyDQaMm4k6zaNZq4ZvipZAVnougyn16CZ8w"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
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
