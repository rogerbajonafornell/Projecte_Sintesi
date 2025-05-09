import os
import json
import requests
import subprocess
import threading
import re
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from dotenv import load_dotenv

from .whisper_service import transcribe_audio
from inventari.models import Article

# Carregar variables d'entorn
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# URLs de l'API de Telegram
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GETFILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"

# Endpoint de Mistral
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Estat intern per a comandes, confirmacions i idioma per xat
pending_orders = {}        # chat_id -> article_name
pending_confirmations = {} # chat_id -> (article_name, quantity)
chat_language = {}         # chat_id -> language code
conversation_history = {}  # chat_id -> list of messages
processed_update_ids = set()
update_lock = threading.Lock()

# Diccionaris de paraules d'afirmació i negació per idioma
YES_NO = {
    'ca': { 'yes': ['si','sí','s','vale',"d'acord"], 'no': ['no','n'] },
    'es': { 'yes': ['si','sí','s','vale','de acuerdo'], 'no': ['no','n'] },
    'en': { 'yes': ['yes','y','ok','sure','yep'], 'no': ['no','n','nope'] }
}

# Missatges de plantilla per idiomes
TEMPLATES = {
    'order_success': {
        'ca': "Has comprat {qty} unitat(s) de {article}. Gràcies per la teva compra!",
        'es': "Has comprado {qty} unidad(es) de {article}. ¡Gracias por tu compra!",
        'en': "You have purchased {qty} unit(s) of {article}. Thank you for your purchase!"
    },
    'out_of_stock': {
        'ca': "Ho sento, només queden {stock} unitats de '{article}'.",
        'es': "Lo siento, solo quedan {stock} unidades de '{article}'.",
        'en': "Sorry, only {stock} units of '{article}' remain."
    },
    'order_cancelled': {
        'ca': "Comanda cancel·lada.",
        'es': "Pedido cancelado.",
        'en': "Order cancelled."
    },
    'confirm_prompt': {
        'ca': "Vols confirmar la compra de {qty} {article}?",
        'es': "¿Deseas confirmar la compra de {qty} {article}?",
        'en': "Do you want to confirm the purchase of {qty} {article}?"
    }
}

# Prompt de sistema milloritzat amb exemples (few-shot)
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ets ShopMate, un assistent de compres conversacional. "
        "Segueix sempre aquest flux:\n"
        "1️⃣ Si NO s'ha definit article, pregunta a l'usuari quin article vol (action=ask, article=null, quantity=null).\n"
        "2️⃣ Quan l'usuari respon un nom d'article, normalitza (minúscula, singular) i retorna action=search, article=<nom>, quantity=null i un message en llenguatge natural: 'Quantes unitats de <article> vols?'.\n"
        "3️⃣ Si s'ha definit article i l'usuari respon amb una quantitat numèrica, retorna action=confirm, article=<nom>, quantity=<int> i un message: 'Vols confirmar la compra de <quantity> <article>?'.\n"
        "4️⃣ Si l'usuari confirma (sí), action=order i envia un message de confirmació; si cancel·la (no), action=cancel i message de cancel·lació.\n"
        "🔄 Mantingues sempre l'idioma de l'últim missatge de l'usuari i posa'l a language.\n"
        "🔍 No preguntis mai el 'tipus' d'article, només busca el nom proporcionat.\n"
        "📦 Retorna exclusivament un JSON amb claus: action ∈ {ask,search,confirm,order,cancel}, article: string|null, quantity: int|null, message: string, language: string."
        
    )
}

@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Mètode no permès")
    print("\n🚀 Webhook received")
    threading.Thread(target=process_update, args=(request.body,)).start()
    return JsonResponse({'status': 'received'})


def call_mistral(messages):
    data = {"model": "mistral-small", "messages": messages, "temperature": 0.2, "response_format": {"type": "json_object"}}
    resp = requests.post(MISTRAL_API_URL, headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}, json=data)
    print(f"⚙️ [Mistral] Status: {resp.status_code}")
    print(f"⚙️ [Mistral] Content: {resp.text}\n")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def process_update(body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON: {body}")
        return

    update_id = data.get('update_id')
    with update_lock:
        if update_id in processed_update_ids:
            print(f"⚠️ Duplicate update_id {update_id}")
            return
        processed_update_ids.add(update_id)

    msg = data.get('message', {})
    chat_id = msg.get('chat', {}).get('id')
    print(f"👤 Chat ID: {chat_id}")
    if not chat_id:
        return

    if 'voice' in msg:
        transcription, err = handle_voice_message(msg['voice']['file_id'])
        if transcription is None:
            print(f"⚠️ Voice Error: {err}")
            send_telegram_message(chat_id, err)
            return
        user_text = transcription.strip()
    else:
        user_text = (msg.get('text') or '').strip()
    print(f"💬 User: {user_text}")

    lang = chat_language.get(chat_id, 'ca')

    # ── SI TENIM UNA COMANDA PENDENT, gestionem el SÍ/NO localment ─────────────
    if chat_id in pending_confirmations:
        art, qty = pending_confirmations[chat_id]
        low = user_text.lower().strip()
        yes_list = YES_NO.get(chat_language.get(chat_id,'ca'),{}).get('yes',[])
        no_list  = YES_NO.get(chat_language.get(chat_id,'ca'),{}).get('no',[])

        # Confirmació local
        if any(re.fullmatch(rf".*\b{re.escape(w)}\b.*", low) for w in yes_list):
            # fem l'order directament
            pending_confirmations.pop(chat_id)
            art_obj = buscar_article(art)
            if art_obj:
                print(f"📦 Stock Before: {art_obj.Unidades}")
                actualitzar_unidades(art_obj, qty)
                print(f"📦 Stock After: {art_obj.Unidades}")
            send_telegram_message(chat_id, TEMPLATES['order_success'][chat_language[chat_id]].format(qty=qty, article=art))
            conversation_history.pop(chat_id, None)
            return

        # Cancel·lació local
        if any(re.fullmatch(rf".*\b{re.escape(w)}\b.*", low) for w in no_list):
            pending_confirmations.pop(chat_id)
            send_telegram_message(chat_id, TEMPLATES['order_cancelled'][chat_language[chat_id]])
            conversation_history.pop(chat_id, None)
            return

        # Si no reconeixem clarament sí/no, reengage a Mistral
        history = conversation_history.setdefault(chat_id, [])
        history.append({"role": "user", "content": user_text})
        result = call_mistral([SYSTEM_PROMPT] + history)
        payload = json.loads(result)        
        if isinstance(payload, list): payload = payload[0]
        # només pop si Mistral demana “order” o “cancel”
        if payload.get('action') in ('order','cancel'):
            pending_confirmations.pop(chat_id)
            if payload.get('action') == 'order':
                art_obj = buscar_article(art)
                if art_obj:
                    actualitzar_unidades(art_obj, qty)
        conversation_history.pop(chat_id, None)
        return

    if chat_id in pending_orders and re.fullmatch(r"\d+", user_text):
        qty = int(user_text)
        art = pending_orders.pop(chat_id)
        print(f"🔢 Received Qty: {qty} for {art}")
        history = conversation_history.setdefault(chat_id, [])
        history.append({"role": "user", "content": user_text})
        result = call_mistral([SYSTEM_PROMPT] + history)
        print(f"🔢 Mistral Qty Result: {result}")
        payload = json.loads(result)
        if isinstance(payload, list): payload = payload[0]
        send_telegram_message(chat_id, payload['message'])
        if payload.get('action') == 'confirm':
            pending_confirmations[chat_id] = (art, qty)
        return

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})
    result = call_mistral([SYSTEM_PROMPT] + history)
    print(f"💡 Mistral Normal Result: {result}")
    payload = json.loads(result)
    if isinstance(payload, list): payload = payload[0]

    action = payload.get('action')
    article = payload.get('article')
    qty = payload.get('quantity')
    message = payload.get('message')
    lang = payload.get('language', lang)
    chat_language[chat_id] = lang
    print(f"🎯 Payload: action={action}, article={article}, qty={qty}, lang={lang}")

    if action == 'search' and article:
        art_obj = buscar_article(article)
        if not art_obj:
            send_telegram_message(chat_id, f"❌ Ho sento, no trobo l'article '{article}'.")
            return
        pending_orders[chat_id] = art_obj.DescripcionArticulo
        print(f"🛒 Pending Order Set: {art_obj.DescripcionArticulo}")

    send_telegram_message(chat_id, message)

    if action == 'confirm' and article and isinstance(qty, int):
        pending_confirmations[chat_id] = (article, qty)
        print(f"🔔 Pending Confirmation Set: {article} x{qty}")
    elif action == 'cancel':
        conversation_history.pop(chat_id, None)
        print(f"🚫 Conversation Cancelled for chat {chat_id}")


def send_telegram_message(chat_id, text):
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
        print(f"📨 Sent to {chat_id}: {text}")
    except Exception as e:
        print(f"⚠️ Error Sending Message: {e}")


def buscar_article(descripcio):
    key = descripcio.strip().lower().rstrip('s')
    try:
        return Article.objects.get(DescripcionArticulo__iexact=key)
    except Article.DoesNotExist:
        return None


def actualitzar_unidades(article, quantitat):
    article.Unidades -= quantitat
    article.save()
    print(f"📦 Stock Updated: {article.DescripcionArticulo} -> {article.Unidades}")


def convert_ogg_to_wav(input_file, output_file):
    command = ['ffmpeg', '-y', '-i', input_file, '-ac', '1', '-ar', '16000', output_file]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def handle_voice_message(file_id):
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
    with open(ogg_path, 'wb') as f:
        f.write(resp.content)

    convert_ogg_to_wav(ogg_path, wav_path)
    transcription, language = transcribe_audio(wav_path)
    os.remove(ogg_path)
    os.remove(wav_path)
    return transcription, language
