from django.shortcuts import render
import json
import requests
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from dotenv import load_dotenv

# Importem el servei de transcripció
from .whisper_service import transcribe_audio
from telegram import Bot  # Utilitzem aquest import per obtenir el fitxer d'àudio

import subprocess
from asgiref.sync import async_to_sync

# Carregar variables d'entorn des de .env
load_dotenv()

# Tokens necessaris
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# URLs de les API
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def get_mistral_response(user_message):
    """ Envia un missatge a Mistral AI i retorna la seva resposta. """
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    # Prompt per a definir el comportament de la IA
    system_prompt = {
        "role": "system",
        "content": """Ets un assistent especialitzat en gestió de comandes. Detecta:
            1. Nom de l'article (ex: 'Samarreta VERMELLA talla M')
            2. Quantitat demanada (ex: '3 unitats')
            Si es detecten ambdós, retorna format ARTICLE:QUANTITY. Exemple: 'SAMARRETAVERMELLA_M:3'"""
    }

    data = {
        "model": "mistral-small",
        "messages": [system_prompt, {"role": "user", "content": user_message}],
        "temperature": 0.7
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
    """  mistral_response = response.json()['choices'][0]['message']['content']

        if ":" in mistral_response:
            article, quantity = mistral_response.split(":", 1)
            print( {"article": article.strip(), "quantity": int(quantity)})
            return {"article": article.strip(), "quantity": int(quantity)}
        else:
            return {"error": "No s'ha detectat sol·licitud vàlida"}
        """
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return "No puc respondre en aquest moment. Torna-ho a intentar més tard."

def send_telegram_message(chat_id, text):
    """ Envia un missatge a Telegram """
    payload = {"chat_id": chat_id, "text": text}
    requests.post(TELEGRAM_URL, json=payload)


import subprocess

def convert_ogg_to_wav(input_file, output_file):
    command = [
        'ffmpeg',
        '-y',            # Sobreescriu el fitxer de sortida si existeix
        '-i', input_file,
        '-ac', '1',      # Canal mono
        '-ar', '16000',  # Taxa de mostreig 16 kHz
        output_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("Error en la conversió amb ffmpeg:")
        print(result.stderr)
    return result.returncode



def handle_voice_message(file_id):
    """Baixa, converteix i transcriu el missatge de veu rebut des de Telegram"""
    bot = Bot(token=TELEGRAM_TOKEN)
    file_info = async_to_sync(bot.get_file)(file_id)
    file_path_from_api = file_info.file_path
    print("File URL obtingut:", file_path_from_api)
    
    # Comprova si file_path_from_api ja és una URL completa
    if file_path_from_api.startswith("http"):
        download_url = file_path_from_api
    else:
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path_from_api}"
    
    print("Download URL:", download_url)
    
    ogg_path = f"temp/{file_id}.ogg"
    response = requests.get(download_url)
    print("Response status:", response.status_code)
    print("Mida del contingut descarregat:", len(response.content))
    
    os.makedirs("temp", exist_ok=True)
    with open(ogg_path, "wb") as f:
        f.write(response.content)
    
    # Comprovem que el fitxer OGG s'ha descarregat correctament
    if not response.ok or os.path.getsize(ogg_path) == 0:
        print("Error: el fitxer OGG està buit o la descàrrega ha fallat.")
        return "Error en la descàrrega de l'àudio."
    
    # Converteix el fitxer OGG a WAV
    wav_path = f"temp/{file_id}.wav"
    ret = convert_ogg_to_wav(ogg_path, wav_path)
    if ret != 0 or not os.path.exists(wav_path):
        os.remove(ogg_path)
        return "Error en la conversió d'àudio."
    
    # Transcriu el fitxer WAV amb faster-whisper
    transcription, language = transcribe_audio(wav_path)
    
    # Neteja els fitxers temporals
    os.remove(ogg_path)
    os.remove(wav_path)
    
    return f"[{language.upper()}] {transcription}"


@csrf_exempt
def telegram_webhook(request):
    """ Gestiona els missatges entrants de Telegram (text i veu) i respon amb Mistral AI. """
    print("📩 Webhook rebut!")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📜 Dades rebudes:", data)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("⚠️ JSON no vàlid")

        if 'message' in data:
            chat_id = data['message']['chat']['id']

            # Si el missatge és de text
            if 'text' in data['message']:
                user_message = data['message']['text']
                # Obtenim la resposta de Mistral AI
                response_text = get_mistral_response(user_message)
                send_telegram_message(chat_id, response_text)

            # Si el missatge és de veu
            elif 'voice' in data['message']:
                file_id = data['message']['voice']['file_id']
                transcribed_text = handle_voice_message(file_id)
                # Pots enviar la transcripció directament o processar-la amb Mistral
                response_text = get_mistral_response(transcribed_text)
                send_telegram_message(chat_id, response_text)

        return JsonResponse({'status': 'ok'})
    else:
        return HttpResponseBadRequest("⚠️ Mètode no permès")
