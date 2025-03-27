import os
import requests
from dotenv import load_dotenv  # Importem dotenv per carregar variables d'entorn

# Carregar el fitxer .env
load_dotenv()

# Obtenir la API Key des de .env
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Comprovar que tenim la API Key
if not MISTRAL_API_KEY:
    print("⚠️ Error: No s'ha trobat la API Key. Assegura't que el fitxer .env és correcte.")
    exit(1)

# Configurar la petició
headers = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "mistral-small",
    "messages": [{"role": "user", "content": "Hola! Aquest és un test de connexió."}]
}

# Fer la petició a l'API de Mistral
try:
    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        resposta = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print("✅ Connexió correcta!")
        print(f"📩 Resposta de Mistral: {resposta}")
    else:
        print(f"⚠️ Error {response.status_code}: {response.text}")

except requests.RequestException as e:
    print(f"❌ Error en la connexió: {e}")
