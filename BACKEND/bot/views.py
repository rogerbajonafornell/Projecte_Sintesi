import os
import json
import logging
import requests
import subprocess
import threading
import time
import re
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from dotenv import load_dotenv

from .whisper_service import transcribe_audio
from inventari.models import Article
from .models import Usuari

# --- Configuració de logging per depuració ---
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Carregar variables d'entorn
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# URLs de l'API de Telegram
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GETFILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"

# Endpoint de Mistral
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Estat intern per a comandes i confirmacions
pending_orders = {}        # chat_id -> article_desc
pending_confirmations = {} # chat_id -> (Article, quantity)

# Deduplciació d'updates
processed_update_ids = set()
update_lock = threading.Lock()

# Prompt de sistema per donar control a la IA
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ets ShopMate, un assistent de compres conversacional. "
        "Decideix tu mateix què fer en cada moment: parlar de manera natural, preguntar a l'usuari, buscar un article, demanar confirmació, etc. No mostris mai JSON brut al client; utilitza sempre text natural. "
        "Detecta l'idioma de l'usuari i respon sempre en aquest idioma. "
        "Retorna només un JSON amb claus: action ∈ {ask,search,order,confirm,cancel}, article: string|null, quantity: int|null, message: string, language: string."
    )
}

@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Mètode no permès")
    threading.Thread(target=process_update, args=(request.body,)).start()
    return JsonResponse({'status': 'received'})


def call_mistral(messages):
    data = {
        "model": "mistral-small",
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    resp = requests.post(
        MISTRAL_API_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json=data
    )
    logger.debug("Mistral status %s: %s", resp.status_code, resp.text)
    if resp.status_code != 200:
        raise RuntimeError("Mistral error: %s" % resp.text)
    return resp.json()["choices"][0]["message"]["content"]


def process_update(body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.error("JSON no vàlid al webhook: %s", body)
        return

    update_id = data.get('update_id')
    with update_lock:
        if update_id in processed_update_ids:
            logger.debug("Ignorant update_id duplicat: %s", update_id)
            return
        processed_update_ids.add(update_id)

    msg = data.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    
    # Guardar/Actualitzar dades de l'usuari
    user_data = msg.get('from', {})
    user_id = user_data.get('id')
    first_name = user_data.get('first_name', '')
    username = user_data.get('username')

    # Crear o actualitzar l'usuari
    Usuari.objects.update_or_create(
        UserId=user_id,
        defaults={
            'FirstName': first_name,
            'Username': username,
        }
    )

    # Gestionar veu
    if 'voice' in msg:
        transcription, err = handle_voice_message(msg['voice']['file_id'])
        if transcription is None:
            send_telegram_message(chat_id, err)
            return
        user_text = transcription
    else:
        user_text = (msg.get('text') or '').strip()

    # Construir conversa per Mistral
    convo = [SYSTEM_PROMPT, {"role": "user", "content": user_text}]
    try:
        result = call_mistral(convo)
    except Exception as e:
        logger.error("Error cridant Mistral: %s", e)
        send_telegram_message(chat_id, "Error amb la IA, torna-ho a intentar.")
        return

    try:
        payload = json.loads(result)
        # Si la IA retorna una llista, agafem el primer element
        if isinstance(payload, list) and payload:
            payload = payload[0]
    except json.JSONDecodeError:
        logger.error("Resposta invàlida de la IA: %s", result)
        send_telegram_message(chat_id, "Resposta invàlida de la IA.")
        return

    action = payload.get('action')
    article = payload.get('article')
    qty = payload.get('quantity')
    message = payload.get('message')
    lang = payload.get('language')

    # Enviar missatge generat per la IA
    send_telegram_message(chat_id, message)

    # Executar accions backend si cal
    if action == 'search' and article:
        art = buscar_article(article)
        if art:
            # Preguntar quantitats de manera natural
            send_telegram_message(chat_id, f"Quantes unitats de '{art.DescripcionArticulo}' vols?")
            pending_orders[chat_id] = art.DescripcionArticulo
        else:
            send_telegram_message(chat_id, f"Ho sento, no trobo l'article '{article}'.")

    elif action == 'order' and article and isinstance(qty, int):
        art = buscar_article(article)
        if art and art.Unidades >= qty:
            actualitzar_unidades(art, qty)
            send_telegram_message(chat_id, f"Compra feta: {qty}× '{art.DescripcionArticulo}'. Gràcies! 😊")
        elif art and art.Unidades == 0:
            send_telegram_message(chat_id, f"Ho sento, l'article '{art.DescripcionArticulo}' està esgotat.")
        else:
            send_telegram_message(chat_id, f"Només queden {art.Unidades if art else 0} unitats de '{article}'. Quantes en vols? 😊")
            pending_orders[chat_id] = article

    # 'confirm' i 'cancel' gestionats per la IA mitjançant message retornat


def send_telegram_message(chat_id, text):
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error("Error enviant missatge Telegram: %s", e)


def buscar_article(descripcio):
    try:
        return Article.objects.get(DescripcionArticulo__iexact=descripcio)
    except Article.DoesNotExist:
        return None


def actualitzar_unidades(article, quantitat):
    article.Unidades -= quantitat
    article.save()


def convert_ogg_to_wav(input_file, output_file):
    command = ['ffmpeg', '-y', '-i', input_file, '-ac', '1', '-ar', '16000', output_file]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode


def handle_voice_message(file_id):
    # Obtenir info de l'arxiu via HTTP
    resp_info = requests.get(TELEGRAM_GETFILE_URL, params={"file_id": file_id})
    if resp_info.status_code != 200:
        return None, "Error obtenint informació de l'àudio"
    info = resp_info.json().get('result', {})
    path = info.get('file_path')
    if not path:
        return None, "Error obtenint ruta de l'àudio"
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{path}"

    os.makedirs('temp', exist_ok=True)
    ogg_path, wav_path = f"temp/{file_id}.ogg", f"temp/{file_id}.wav"

    resp = requests.get(download_url)
    if not resp.ok or not resp.content:
        return None, "Error descarregant àudio"
    with open(ogg_path, 'wb') as f:
        f.write(resp.content)

    if convert_ogg_to_wav(ogg_path, wav_path) != 0:
        os.remove(ogg_path)
        return None, "Error convertint àudio"

    transcription, language = transcribe_audio(wav_path)
    os.remove(ogg_path)
    os.remove(wav_path)
    return transcription, language
