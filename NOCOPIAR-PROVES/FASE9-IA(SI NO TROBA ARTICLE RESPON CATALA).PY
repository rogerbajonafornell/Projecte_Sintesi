import os
import io
import json
import requests
import threading
import re
from openai import OpenAI
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from dotenv import load_dotenv

from inventari.models import Article

# Carregar variables d'entorn
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicialitzar client OpenAI
openai = OpenAI(api_key=OPENAI_API_KEY)

# URLs de l'API de Telegram
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GETFILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"

# Estat intern per a comandes i conversa
pending_orders = {}
pending_confirmations = {}
chat_language = {}
conversation_history = {}
processed_update_ids = set()
update_lock = threading.Lock()

# System prompt per GPT-4 Turbo, gestió automàtica d'idioma
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are ShopMate, a professional, multilingual shopping assistant. "
        "Always ask and answer in the same language as the user’s last message. "
        "Follow this flow and output only JSON with keys: action, article, quantity, message, language."
        "1. If no article named, action=ask, article=null, quantity=null, ask: 'Which item would you like to buy?'."
        "2. When user gives an article name, action=search, article=<name>, quantity=null, ask: 'How many units of <article> do you want?'."
        "3. When user gives a numeric quantity, action=confirm, article=<name>, quantity=<int>, ask: 'Do you confirm purchasing <quantity> of <article>?'."
        "4. If user confirms, action=order; if declines, action=cancel. Generate stock check and dynamic success or out-of-stock messages."
    )
}

# Funció per netejar blocs Markdown

def neteja_resposta(resposta: str) -> str:
    resposta = re.sub(r'```(?:json)?\n?', '', resposta)
    resposta = re.sub(r'```', '', resposta)
    return resposta.strip()

# Funció per enviar errors via IA en l'idioma de la conversa

def ai_send_error(chat_id: int, error_text: str, lang: str):
    # error_text ha de ser en l'idioma detectat (lang)
    history = conversation_history.get(chat_id, [])
    # Formular prompt perquè l'assistent generi un missatge d'error amistós
    history_copy = history.copy()
    history_copy.append({"role": "user", "content": error_text})
    convo = [SYSTEM_PROMPT] + history_copy
    result = call_openai(convo)
    try:
        payload = json.loads(result)
        send_telegram_message(chat_id, payload.get("message", error_text))
    except Exception:
        send_telegram_message(chat_id, error_text)

@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Mètode no permès")
    print("\n🚀 Webhook received")
    threading.Thread(target=process_update, args=(request.body,)).start()
    return JsonResponse({'status': 'received'})


def call_openai(messages):
    print("⚙️ Calling OpenAI GPT-4 Turbo...")
    resp = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=messages,
        temperature=0.2
    )
    content = resp.choices[0].message.content
    print(f"⚙️ OpenAI raw response: {content!r}")
    clean = neteja_resposta(content)
    print(f"⚙️ OpenAI cleaned response: {clean!r}")
    return clean


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

    # Obtenir i registrar text
    if 'voice' in msg:
        print("🎤 Voice message received, transcribing...")
        user_text = handle_voice_message(msg['voice']['file_id']) or ''
        print(f"💬 Transcription: {user_text}")
    else:
        user_text = (msg.get('text') or '').strip()
        print(f"💬 User: {user_text}")

    # Detectar idioma actual o per defecte
    lang = chat_language.get(chat_id, None)

    # Validació prèvia d'article
    m = re.search(r"comprar\s+(?:un |una )?(.+)", user_text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        art_obj = buscar_article(candidate)
        if not art_obj:
            print(f"❌ Article not found (pre-GPT): {candidate}")
            # determinar idioma: si no hem detectat encara, fem primer prompt IA per detectar idioma
            if not lang:
                # fer una trucada breu a GPT per obtenir idioma
                detection = call_openai([SYSTEM_PROMPT, {"role":"user","content":user_text}])
                try:
                    det = json.loads(detection)
                    lang = det.get('language', 'en')
                except:
                    lang = 'en'
            ai_send_error(chat_id, f"Ho sento, no trobo l'article '{candidate}'.", lang)
            return

    # Continuar flux normal
    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})
    convo = [SYSTEM_PROMPT] + history
    result = call_openai(convo)

    if not result:
        ai_send_error(chat_id, "Ho sento, ha ocorregut un error intern. Torna-ho a intentar.", lang or 'en')
        return
    try:
        payload = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decode error: {e}, result was: {result!r}")
        ai_send_error(chat_id, "Ho sento, ha ocorregut un error intern. Torna-ho a intentar.", lang or 'en')
        return

    action = payload.get('action')
    article = payload.get('article')
    qty = payload.get('quantity')
    message = payload.get('message')
    lang = payload.get('language', lang or 'en')
    chat_language[chat_id] = lang
    print(f"🎯 Payload: action={action}, article={article}, qty={qty}, lang={lang}")

    # Error en search via IA
    if action == 'search' and article:
        art_obj = buscar_article(article)
        if not art_obj:
            print(f"❌ Article not found in search: {article}")
            ai_send_error(chat_id, f"Ho sento, no trobo l'article '{article}'.", lang)
            return

    # Enviar missatge final
    history.append({"role": "assistant", "content": message})
    send_telegram_message(chat_id, message)
    print(f"📨 Sent: {message}")

    # Estat pendent
    if action == 'search' and article:
        art_obj = buscar_article(article)
        if art_obj:
            pending_orders[chat_id] = art_obj.DescripcionArticulo
            print(f"🛒 Pending order: {art_obj.DescripcionArticulo}")
    elif action == 'confirm' and article and isinstance(qty, int):
        pending_confirmations[chat_id] = (article, qty)
        print(f"🔔 Pending confirm: {article} x{qty}")
    elif action == 'order' and article and isinstance(qty, int):
        art_obj = buscar_article(article)
        if art_obj and art_obj.Unidades >= qty:
            actualitzar_unidades(art_obj, qty)
            print(f"✅ Processed: {article} x{qty}")
        pending_confirmations.pop(chat_id, None)
        conversation_history.pop(chat_id, None)
        chat_language.pop(chat_id, None)
    elif action == 'cancel':
        print(f"❌ Cancelled: {article}")
        pending_confirmations.pop(chat_id, None)
        conversation_history.pop(chat_id, None)
        chat_language.pop(chat_id, None)


def send_telegram_message(chat_id, text):
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"⚠️ Error sending message: {e}")


def buscar_article(descripcio):
    key = descripcio.strip().lower()
    try:
        return Article.objects.get(DescripcionArticulo__iexact=key)
    except Article.DoesNotExist:
        return None


def actualitzar_unidades(article, quantitat):
    print(f"📦 Stock before update: {article.Unidades}")
    article.Unidades -= quantitat
    article.save()
    print(f"📦 Stock after update: {article.Unidades}")


def handle_voice_message(file_id):
    print(f"⬇️ Downloading voice file {file_id}")
    info = requests.get(TELEGRAM_GETFILE_URL, params={"file_id":file_id}).json().get('result', {})
    ogg = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{info.get('file_path')}").content
    print("🎧 File downloaded, sending to Whisper")
    buf = io.BytesIO(ogg)
    buf.name = 'voice.ogg'
    resp = openai.audio.transcriptions.create(model='whisper-1', file=buf, response_format='text')
    print(f"📝 Transcription result: {resp}")
    return resp
