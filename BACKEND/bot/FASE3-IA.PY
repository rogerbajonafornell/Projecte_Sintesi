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

# --- Configuració de logging per depuració ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# Carregar variables d'entorn
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# URLs de les API
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GETFILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Estat intern per a comandes i confirmacions pendents
pending_orders = {}          # chat_id -> article_desc
pending_confirmations = {}   # chat_id -> (Article, quantity)

# Conjunt d'update_id ja processats per evitar duplicats
processed_update_ids = set()
update_lock = threading.Lock()


def send_telegram_message(chat_id, text):
    logger.debug("Enviant a Telegram (chat_id=%s): %s", chat_id, text)
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
    # Obtenir informació del fitxer via HTTP API per evitar corutines
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


def get_mistral_json_response(user_message, retries=1, backoff=1):
    system_prompt = {
        "role": "system",
        "content": (
            "Ets ShopMate, un assistent de compres empàtic en català. "
            "Si l'usuari inclou un nombre i la paraula 'unitats', assigna intent 'order' i quantity corresponent. "
            "RESPON només amb JSON: intent∈{search,order,confirm,cancel}, article:string|null, quantity:int|null, confirmation:bool|null."
        )
    }
    few_shot = [
        {"role": "user", "content": "vull 2 unitats de l'article cafetera"},
        {"role": "assistant", "content": json.dumps({"intent":"order","article":"cafetera","quantity":2,"confirmation":None})}
    ]
    data = {
        "model": "mistral-small",
        "messages": [system_prompt] + few_shot + [{"role": "user", "content": user_message}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    attempt = 0
    while True:
        attempt += 1
        logger.debug("[Mistral] Intent %s: %s", attempt, data)
        resp = requests.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
            json=data
        )
        logger.debug("Resposta Mistral (status %s): %s", resp.status_code, resp.text)
        if resp.status_code == 200:
            break
        if resp.status_code == 429 and attempt <= retries:
            logger.warning("Rate limit Mistral, reintentant en %s s...", backoff)
            time.sleep(backoff)
            backoff *= 2
            continue
        return {"error": "Error connectant amb Mistral IA."}

    content = resp.json()["choices"][0]["message"]["content"]
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Error parsejant JSON de Mistral: %s", e)
            return {"error": "No t'he entès, pots reformular-ho?"}
    if isinstance(content, dict):
        return content
    return {"error": "Format de resposta inesperat."}


@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Mètode no permès")
    threading.Thread(target=process_update, args=(request.body,)).start()
    return JsonResponse({'status': 'received'})


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

    # Veu: transcriure abans de processar text
    if 'voice' in msg:
        file_id = msg['voice']['file_id']
        transcription, err = handle_voice_message(file_id)
        if transcription is None:
            send_telegram_message(chat_id, err)
            return
        text = transcription
    else:
        text = (msg.get('text') or '').strip()

    # Gestionar salutacions humanes abans de processar intents
    if re.search(r"\b(hola|bon dia|bona tarda|bona nit)\b", text.lower()):
        send_telegram_message(chat_id, "Hola! Sóc ShopMate, el teu assistent de compres. Què t'agradaria comprar avui?")
        return

    # Fallback local per quantitat si ja hi ha article pendent
    if chat_id in pending_orders and re.search(r"\d+", text):
        quantity = int(re.search(r"(\d+)", text).group(1))
        article_desc = pending_orders[chat_id]
        intent = 'order'
        result = {'intent': intent, 'article': article_desc, 'quantity': quantity, 'confirmation': None}
        logger.debug("Fallback parsed result: %s", result)
    else:
        result = get_mistral_json_response(text)
        logger.debug("Result Mistral parsed: %s", result)

    if 'error' in result:
        send_telegram_message(chat_id, result['error'])
        return

    intent = result.get('intent')
    article_desc = result.get('article')
    quantity = result.get('quantity')
    confirmation = result.get('confirmation')

    # SEARCH
    if intent == 'search' and article_desc:
        art = buscar_article(article_desc)
        if not art:
            send_telegram_message(chat_id, f"No trobo l'article '{article_desc}'.")
            return
        pending_orders[chat_id] = art.DescripcionArticulo
        send_telegram_message(chat_id, f"Quantes unitats de '{art.DescripcionArticulo}' vols?")
        return

    # ORDER
    if intent == 'order' and article_desc and quantity is not None:
        art = buscar_article(article_desc)
        if not art:
            send_telegram_message(chat_id, f"No trobo l'article '{article_desc}'.")
            return
        if art.Unidades == 0:
            send_telegram_message(chat_id, f"Ho sento, l'article '{article_desc}' està esgotat.")
            return
        if art.Unidades < quantity:
            pending_orders[chat_id] = art.DescripcionArticulo
            send_telegram_message(chat_id, f"Només queden {art.Unidades} unitats. Quantes en vols?")
            return
        total = quantity * getattr(art, 'Precio', 0)
        pending_confirmations[chat_id] = (art, quantity)
        send_telegram_message(
            chat_id,
            f"Confirmes compra de {quantity}× '{art.DescripcionArticulo}' (total {total}€)? (sí/no)"
        )
        return

    # CONFIRM
    if intent == 'confirm' and confirmation and chat_id in pending_confirmations:
        art, qty = pending_confirmations.pop(chat_id)
        actualitzar_unidades(art, qty)
        send_telegram_message(chat_id, f"Compra feta: {qty}× '{art.DescripcionArticulo}'. Gràcies!")
        return

    # CANCEL
    if intent == 'cancel':
        pending_orders.pop(chat_id, None)
        pending_confirmations.pop(chat_id, None)
        send_telegram_message(chat_id, "Comanda cancel·lada.")
        return

    send_telegram_message(chat_id, "Ho sento, no t'he entès. Pots provar un altre cop?")
