import os
import json
import requests
import subprocess
import re
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from asgiref.sync import async_to_sync
from telegram import Bot
from dotenv import load_dotenv

from .whisper_service import transcribe_audio
from inventari.models import Article

# Carregar variables d'entorn des de .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# URLs de les API
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Estat intern per a comandes i confirmacions pendents
pending_orders = {}          # chat_id -> article_desc
pending_confirmations = {}   # chat_id -> (Article, quantity)


def send_telegram_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    requests.post(TELEGRAM_URL, json=payload)


def buscar_article(descripcio):
    try:
        return Article.objects.get(DescripcionArticulo__iexact=descripcio)
    except Article.DoesNotExist:
        return None


def actualitzar_unidades(article, quantitat):
    article.Unidades -= quantitat
    article.save()


def convert_ogg_to_wav(input_file, output_file):
    command = [
        'ffmpeg', '-y', '-i', input_file,
        '-ac', '1', '-ar', '16000', output_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode


def handle_voice_message(file_id):
    bot = Bot(token=TELEGRAM_TOKEN)
    file_info = async_to_sync(bot.get_file)(file_id)
    path = file_info.file_path
    download_url = path if path.startswith('http') else f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{path}"

    os.makedirs('temp', exist_ok=True)
    ogg_path = f"temp/{file_id}.ogg"
    wav_path = f"temp/{file_id}.wav"

    resp = requests.get(download_url)
    if not resp.ok or len(resp.content) == 0:
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


def get_mistral_json_response(user_message):
    system_prompt = {
        "role": "system",
        "content": (
            "Ets ShopMate, un assistent de compres conversacional i empàtic integrat en Django+Telegram. "
            "Retorna sempre un JSON amb claus: intent (search|order|confirm|cancel), article (o null), quantity (o null), "
            "confirmation (true|false|null). No afegeix res més."
        )
    }
    few_shot = [
        {"role": "user", "content": "Vull una cafetera"},
        {"role": "assistant", "content": json.dumps({
            "intent": "search", "article": "cafetera", "quantity": None, "confirmation": None
        })},
        {"role": "user", "content": "En vull 2"},
        {"role": "assistant", "content": json.dumps({
            "intent": "order", "article": "cafetera", "quantity": 2, "confirmation": None
        })},
        {"role": "user", "content": "Sí, confirma"},
        {"role": "assistant", "content": json.dumps({
            "intent": "confirm", "article": "cafetera", "quantity": 2, "confirmation": True
        })}
    ]

    data = {
        "model": "mistral-small",
        "messages": [system_prompt] + few_shot + [{"role": "user", "content": user_message}],
        "temperature": 0.0
    }
    resp = requests.post(
        MISTRAL_API_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json=data
    )
    if resp.status_code != 200:
        return {"error": "Error connectant amb Mistral IA."}

    content = resp.json().get("choices", [])[0].get("message", {}).get("content", "").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"error": f"Resposta invàlida: {content}"}
    return parsed

@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Mètode no permès")
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON no vàlid")

    message = body.get('message', {})
    chat_id = message.get('chat', {}).get('id')
    text = (message.get('text') or '').strip()

    # Veu
    if 'voice' in message:
        file_id = message['voice']['file_id']
        transcription, err = handle_voice_message(file_id)
        if transcription is None:
            send_telegram_message(chat_id, err)
            return JsonResponse({'status': 'voice_error'})
        text = transcription

    # Invocar Mistral per obtenir JSON d'intents
    if text:
        result = get_mistral_json_response(text)
        if 'error' in result:
            send_telegram_message(chat_id, result['error'])
            return JsonResponse({'status': 'ai_error'})

        intent = result.get('intent')
        article_desc = result.get('article')
        quantity = result.get('quantity')
        confirmation = result.get('confirmation')

        # SEARCH intent
        if intent == 'search' and article_desc:
            art = buscar_article(article_desc)
            if not art:
                send_telegram_message(chat_id, f"No trobo l'article '{article_desc}'.")
                return JsonResponse({'status': 'article_not_found'})
            pending_orders[chat_id] = art.DescripcionArticulo
            send_telegram_message(chat_id, f"Quantes unitats de '{art.DescripcionArticulo}' vols?")
            return JsonResponse({'status': 'awaiting_quantity'})

        # ORDER intent
        if intent == 'order' and article_desc and quantity is not None:
            art = buscar_article(article_desc)
            if not art:
                send_telegram_message(chat_id, f"No trobo l'article '{article_desc}'.")
                return JsonResponse({'status': 'article_not_found'})
            if art.Unidades < quantity:
                pending_orders[chat_id] = art.DescripcionArticulo
                send_telegram_message(chat_id, f"Només queden {art.Unidades} unitats. Quantes en vols?")
                return JsonResponse({'status': 'insufficient_stock'})
            total = quantity * getattr(art, 'Precio', 0)
            pending_confirmations[chat_id] = (art, quantity)
            send_telegram_message(chat_id, f"Confirmes compra de {quantity}× '{art.DescripcionArticulo}' (total {total}€)? (sí/no)")
            return JsonResponse({'status': 'awaiting_confirmation'})

        # CONFIRM intent
        if intent == 'confirm' and confirmation and chat_id in pending_confirmations:
            art, qty = pending_confirmations.pop(chat_id)
            actualitzar_unidades(art, qty)
            send_telegram_message(chat_id, f"Compra feta: {qty}× '{art.DescripcionArticulo}'. Gràcies!")
            return JsonResponse({'status': 'order_completed'})

        # CANCEL intent
        if intent == 'cancel':
            pending_orders.pop(chat_id, None)
            pending_confirmations.pop(chat_id, None)
            send_telegram_message(chat_id, "Comanda cancel·lada.")
            return JsonResponse({'status': 'order_cancelled'})

    return JsonResponse({'status': 'ok'})
