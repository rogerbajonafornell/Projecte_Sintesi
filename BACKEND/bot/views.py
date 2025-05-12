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
from decimal import Decimal
from inventari.models import Article
from bot.models import Comanda, Usuari
from .serializers import UsuariSerializer, ComandaSerializer
from rest_framework import generics
 
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
pending_orders = {}        # chat_id -> article_name
pending_confirmations = {} # chat_id -> (article_name, quantity)
chat_language = {}         # chat_id -> language code
conversation_history = {}  # chat_id -> list of messages
processed_update_ids = set()
update_lock = threading.Lock()

# System prompt per GPT-4 Turbo, gestió automàtica d'idioma
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are ShopMate, a professional, multilingual shopping assistant. "
        "Always ask and answer in the same language as the user’s last message. "
        "Follow this flow and output only JSON with keys: action, article, quantity, message, language.\n\n"
        "1. If no article named, action=ask, article=null, quantity=null, ask: 'Which item would you like to buy?'.\n"
        "2. When user gives an article name, action=search, article=<name>, quantity=null, ask: 'How many units of <article> do you want?'.\n"
        "3. When user gives a numeric quantity, action=confirm, article=<name>, quantity=<int>, ask: 'Do you confirm purchasing <quantity> of <article>?'.\n"
        "4. If user confirms, action=order; if declines, action=cancel. "
        "Generate stock check and dynamic success or out-of-stock messages."
    )
}

# Funció per netejar la resposta GPT de blocs Markdown abans de parsejar JSON
def neteja_resposta(resposta: str) -> str:
    """
    Elimina qualsevol bloc de codi Markdown ``` o ```json```
    i retorna la cadena neta per fer json.loads().
    """
    print(f"⚙️ Cleaning response: {resposta!r}")
    resposta = re.sub(r'```(?:json)?\n?', '', resposta)
    resposta = re.sub(r'```', '', resposta)
    clean = resposta.strip()
    print(f"⚙️ Cleaned response: {clean!r}")
    return clean

def generate_error_message(chat_id, error_context):
    """Genera un missatge d'error personalitzat amb OpenAI."""
    prompt = f"""
    Genera un missatge d'error amigable i concís en l'idioma de l'usuari per a un bot de Telegram.
    Context de l'error: {error_context}.
    No incloguis explicacions tècniques, només un missatge per a l'usuari.
    """
    try:
        error_result = call_openai([{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        if error_result:
            payload = json.loads(error_result)
            return payload.get("message", "Ho sento, hi ha hagut un error intern. Torna-ho a intentar.")
    except Exception:
        # Missatge de reserva si la crida falla
        return "Ho sento, hi ha hagut un error intern. Torna-ho a intentar."
    return "Ho sento, hi ha hagut un error intern. Torna-ho a intentar."

def generar_comanda(article_id, preu_u, quantitat, user_id):
    from decimal import Decimal
    from bot.models import Usuari, Comanda
    from inventari.models import Article

    # 1️⃣ Carregar instàncies relacionades
    usuari_obj  = Usuari.objects.get(pk=user_id)
    article_obj = Article.objects.get(pk=article_id)

    # 2️⃣ Calcular total amb Decimal
    preu_u_dec = Decimal(str(preu_u))
    total      = preu_u_dec * Decimal(quantitat)

    print(f"Creant comanda -> user:{usuari_obj}, article:{article_obj}, qty:{quantitat}, total:{total}")

    # 3️⃣ Crear Comanda amb kwargs
    comanda = Comanda.objects.create(
        user      = usuari_obj,
        article   = article_obj,
        Quantitat = quantitat,
        PreuFinal = total
    )

    print(f"Comanda desada: {comanda}")
    return comanda


@csrf_exempt
def telegram_webhook(request):
    print(f"🚀 Webhook hit with method {request.method}")
    if request.method != 'POST':
        print("⚠️ Invalid method, returning 400")
        return HttpResponseBadRequest("Mètode no permès")
    threading.Thread(target=process_update, args=(request.body,)).start()
    return JsonResponse({'status': 'received'})


def call_openai(messages):
    print(f"⚙️ Calling OpenAI with messages: {messages}")
    resp = openai.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=messages,
    temperature=0.2,
    response_format={"type": "json_object"} #importanttttt
    )
    content = resp.choices[0].message.content
    print(f"⚙️ OpenAI raw response: {content!r}")
    clean = neteja_resposta(content)
    return clean


def process_update(body):
    print(f"🔄 process_update received body: {body}")
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

    if 'voice' in msg:
        print("🎤 Voice message detected")
        user_text = handle_voice_message(msg['voice']['file_id']) or ''
    else:
        user_text = (msg.get('text') or '').strip()
    print(f"💬 User text: {user_text}")

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})
    print(f"📚 Conversation history: {history}")

    convo = [SYSTEM_PROMPT] + history
    result = call_openai(convo)

    # Codi principal
    if not result:
        print("⚠️ No result from OpenAI, sending custom error message")
        error_message = generate_error_message(chat_id, "No s'ha rebut cap resposta d'OpenAI.")
        send_telegram_message(chat_id, error_message)
        return

    try:
        payload = json.loads(result)
        print(f"✅ Parsed payload: {payload}")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decode error: {e}, result was: {result!r}")
        error_message = generate_error_message(chat_id, "La resposta rebuda no té un format vàlid.")
        send_telegram_message(chat_id, error_message)
        return

    action = payload.get('action')
    article = payload.get('article')
    qty = payload.get('quantity')
    message = payload.get('message')
    lang = payload.get('language', chat_language.get(chat_id, 'en'))
    chat_language[chat_id] = lang
    print(f"🎯 Action: {action}, Article: {article}, Quantity: {qty}, Language: {lang}")

    # Interceptar 'search' per validar stock abans de demanar unitats
    if action == 'search' and article:
        art_obj = buscar_article(article)
        if not art_obj:
            print(f"❌ Article not found: {article}")
            #prompt que es passa a la ia quan no es trova l'article.
            error_prompt = (
                f"You are a helpful assistant responding in {lang}. "
                f"The user requested an article '{article}' that does not exist in inventory. "
                "Write a polite, user-friendly error message in the same language, "
                "and suggest checking the name or trying a different product. "
                "Please respond in JSON format with a 'message' key containing the error text."
            )
            ai_error = call_openai([
                {"role": "system", "content": "Generate user-facing error messages in JSON format."},
                {"role": "user", "content": error_prompt}
            ])
            error_message = json.loads(ai_error)["message"]
            print(f"📨 Sending AI-generated error: {error_message}")
            send_telegram_message(chat_id, error_message)
            conversation_history.pop(chat_id, None)
            return

    # Enviar missatge generat per GPT
    print(f"📨 Sending message to user: {message}")
    history.append({"role": "assistant", "content": message})
    send_telegram_message(chat_id, message)

    # Gestionar estats pendents
    if action == 'search' and article:
        art_obj = buscar_article(article)
        if art_obj:
            pending_orders[chat_id] = art_obj.DescripcionArticulo
            print(f"🛒 Pending order: {pending_orders[chat_id]}")

    elif action == 'confirm' and article and isinstance(qty, int):
        pending_confirmations[chat_id] = (article, qty)
        print(f"🔔 Pending confirmation: {pending_confirmations[chat_id]}")

    elif action == 'order' and article and isinstance(qty, int):
        art_obj = buscar_article(article)
        if art_obj and art_obj.Unidades >= qty:
            actualitzar_unidades(art_obj, qty)
            generar_comanda(art_obj.CodigoArticulo,art_obj.PVP,qty,user_id)
            print(f"✅ Order processed: {article} x{qty}")

        else:
            print(f"⚠️ Out of stock for {article}")
        pending_confirmations.pop(chat_id, None)
        conversation_history.pop(chat_id, None)
        chat_language.pop(chat_id, None)

    elif action == 'cancel':
        print(f"❌ Order cancelled for: {article}")
        pending_confirmations.pop(chat_id, None)
        conversation_history.pop(chat_id, None)
        chat_language.pop(chat_id, None)


def send_telegram_message(chat_id, text):
    print(f"🚀 send_telegram_message -> chat_id: {chat_id}, text: {text}")
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"⚠️ Error sending message: {e}")


def buscar_article(descripcio):
    key = descripcio.strip().lower()
    print(f"🔍 buscar_article -> key: {key}")
    try:
        art = Article.objects.get(DescripcionArticulo__iexact=key)
        print(f"✅ Article found: {art}")
        return art
    except Article.DoesNotExist:
        print(f"❌ Article.DoesNotExist for key: {key}")
        return None


def actualitzar_unidades(article, quantitat):
    print(f"📦 Stock before: {article.Unidades}")
    article.Unidades -= quantitat
    article.save()
    
    print(f"📦 Stock after: {article.Unidades}")


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
    

class UsuariListAPIView(generics.ListAPIView):
    queryset = Usuari.objects.all()
    serializer_class = UsuariSerializer

class ComandaListAPIView(generics.ListAPIView):
    queryset = Comanda.objects.all()
    serializer_class = ComandaSerializer
    
class ComandaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comanda.objects.all()
    serializer_class = ComandaSerializer
    lookup_field = 'ComandaId'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        article = instance.Article

        # Sumar la cantidad de vuelta al inventario
        article.Unidades += instance.Quantitat
        article.save()

        # Eliminar la comanda
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)