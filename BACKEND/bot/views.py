import os, io, json, requests, threading, re
from openai import OpenAI
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from dotenv import load_dotenv
from decimal import Decimal
from django.db.models import Case, When
from .utils import search_similar_articles
from inventari.models import Article
from bot.models import Comanda, Usuari
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import ComandaSerializer, UsuariSerializer, ArticleSerializer
from django.db.models.functions import Trim


# Carregar variables d'entorn del fitxer .env
load_dotenv()

# Obté tokens d'API des de les variables d'entorn
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicialitzar client OpenAI
openai = OpenAI(api_key=OPENAI_API_KEY)

# Inicialitza client d'OpenAI amb la clau d'accés
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GETFILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"

# Estat intern per a comandes i conversa
pending_orders = {}        # chat_id -> Article object
pending_confirmations = {} # chat_id -> (Article object, quantity)
pending_selections = {}    # chat_id -> list[Article] for similar articles
chat_language = {}         # chat_id -> language code
conversation_history = {}  # chat_id -> list of messages
processed_update_ids = set() # conjunt d'update_id ja processats
update_lock = threading.Lock() # bloqueig per sincronitzar comprovacions d'update_id

# Prompt del sistema que guia les respostes de l'assistent OpenAI
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are ShopMate, a professional, multilingual shopping assistant. "
        "Always ask and answer in the same language as the user’s last message. "
        "Use the user's first name naturally in your responses. "
        "Important: When the user provides an article name, translate it to Spanish for the 'article' field in the JSON output, as the database uses Spanish names. "
        "In the messages you generate, use the article name in the user's language. "
        "Follow this flow and output only JSON with keys: action, article, quantity, message, language.\n\n"
        "1. If no article is named, set action='ask', article=null, quantity=null, and generate a natural message asking for the item, e.g., 'What can I help you find today, {first_name}?'.\n"
        "2. When an article name is provided, translate it to Spanish, set action='search', article=<Spanish name>, quantity=null, and generate a message asking for the quantity, e.g., 'How many <article in user's language> would you like, {first_name}?'.\n"
        "3. When a quantity is provided, set action='confirm', article=<Spanish name>, quantity=<int>, and generate a confirmation message, e.g., 'Please confirm your purchase of <quantity> <article in user's language>, {first_name}.'.\n"
        "4. If confirmed, set action='order'; if declined, set action='cancel'. For action='order', set message=null. For action='cancel', generate a cancellation message.\n"
        "Ensure your messages are natural, polite, and helpful.\n"
        "You must be very careful at the languages conversation. If client message is in catalan 'ca', don't change to 'es'"
    )
}

def neteja_resposta(resposta: str) -> str:
    """
    Elimina qualsevol bloc de codi Markdown ``` o ```json```
    i retorna la cadena neta per fer json.loads().
    """
    #print(f"⚙️ Cleaning response: {resposta!r}")
    resposta = re.sub(r'```(?:json)?\n?', '', resposta)
    resposta = re.sub(r'```', '', resposta)
    clean = resposta.strip()
    print(f"⚙️ Cleaned response: {clean!r}")
    return clean

def call_openai(messages, model="gpt-4o-2024-08-06", response_format=None):
    """
    Fa una crida de completació de xat a OpenAI i retorna la cadena neta.
    Permet especificar un response_format (per exemple, JSON object).
    """
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if response_format:
        kwargs["response_format"] = response_format
    
    resp = openai.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content
    print(f"⚙️ OpenAI raw response: {content!r}")
    clean = neteja_resposta(content)
    return clean

def translate_message(message_template, lang, **kwargs):
    """
    Formata un template de missatge amb kwargs i el tradueix a l'idioma `lang`,
    preservant noms de productes.
    """

    print("\n\n\n Tanslate message ")
    message = message_template.format(**kwargs)
    print("Tanslate message\n\n\n")
    prompt = f"Translate the following message to {lang}, but do not translate the product names: '{message}'"
    translated = call_openai([{"role": "user", "content": prompt}])
    return translated

def translate_text(text, target_lang, source_lang=None, model="gpt-3.5-turbo"):
       """
        Traducció de text arbitrari des de source_lang (si s'especifica) a target_lang.
       """
       print("\n\n\n Tanslate text \n\n\n")
       prompt = f"Translate '{text}' to {target_lang}"
       if source_lang:
           prompt = f"Translate '{text}' from {source_lang} to {target_lang}"
       response = call_openai([{"role": "user", "content": prompt}], model=model)
       return response.strip()


def send_telegram_message(chat_id, text):
    """
    Envia un missatge de text pla al `chat_id` indicat mitjançant l'endpoint sendMessage de Telegram.
    """
    print(f"🚀 send_telegram_message -> chat_id: {chat_id}, text: {text}")
    try:
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"⚠️ Error sending message: {e}")



def buscar_article(descripcio):
    """
    Cerque un Article per DescripcionArticulo exacta (sense diferenciar majúsc./minúsc.).
    Si no existeix, cerca similars amb search_similar_articles.
    Retorna Article, queryset de similars o None si no hi ha resultats.
    """
    key = descripcio.strip().lower()
    print(f"🔍 buscar_article -> key: {key}")
    try:
        art = Article.objects.annotate(trimmed_desc=Trim('DescripcionArticulo')).get(trimmed_desc__iexact=key)
        print(f"✅ Article found: {art}")
        return art
    except Article.DoesNotExist:
        print(f"❌ Article.DoesNotExist for key: {key}")
        similar_ids = search_similar_articles(key)
        if similar_ids:
            similar_articles = Article.objects.filter(CodigoArticulo__in=similar_ids)
            print(f"🔍 Found similar articles: {[a.DescripcionArticulo for a in similar_articles]}")
            return similar_articles
        else:
            print(f"❌ No similar articles found")
            return None
        
def actualitzar_unidades(article, quantitat):
    """
    Retira `quantitat` de `article.Unidades` i desa el canvi.
    """
    print(f"📦 Stock before: {article.Unidades}")
    article.Unidades -= quantitat
    article.save()
    print(f"📦 Stock after: {article.Unidades}")

def handle_voice_message(file_id):
    """
    Descarrega un missatge de veu de Telegram,
    envia'l a Whisper per transcriure i retorna el text.
    """
    print(f"⬇️ Downloading voice file {file_id}")
    info = requests.get(TELEGRAM_GETFILE_URL, params={"file_id":file_id}).json().get('result', {})
    ogg = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{info.get('file_path')}").content
    print("🎧 File downloaded, sending to Whisper")
    buf = io.BytesIO(ogg)
    buf.name = 'voice.ogg'
    resp = openai.audio.transcriptions.create(model='whisper-1', file=buf, response_format='text')
    print(f"📝 Transcription result: {resp}")
    return resp

def generar_comanda(article_id, preu_u, quantitat, user_id):
    """
    Crea un nou registre Comanda:
      - Cerca Usuari i Article per PK
      - Calcula total = Decimal(preu_u) * quantitat
      - Desa i retorna la Comanda
    """
    from decimal import Decimal
    from bot.models import Usuari, Comanda
    from inventari.models import Article

    usuari_obj = Usuari.objects.get(pk=user_id)
    article_obj = Article.objects.get(pk=article_id)

    preu_u_dec = Decimal(str(preu_u))
    total = preu_u_dec * Decimal(quantitat)

    print(f"Creant comanda -> user:{usuari_obj}, article:{article_obj}, qty:{quantitat}, total:{total}")

    comanda = Comanda.objects.create(
        user=usuari_obj,
        article=article_obj,
        Quantitat=quantitat,
        PreuFinal=total
    )

    print(f"Comanda desada: {comanda}")
    return comanda

ll = None
@csrf_exempt
def telegram_webhook(request):
    """
    Vista Django per rebre actualitzacions de webhook de Telegram.
    Processa només POST i llança un fil nou per processar cada actualització.
    """
    print(f"🚀 Webhook hit with method {request.method}")
    if request.method != 'POST':
        print("⚠️ Invalid method, returning 400")
        return HttpResponseBadRequest("Mètode no permès")
    threading.Thread(target=process_update, args=(request.body,)).start()

    return JsonResponse({'status': 'received'})


def process_update(body):
    global ll
    """
    Gestor principal d'actualitzacions Telegram:
    - Desserialitza el JSON rebut
    - Evita duplicats mitjançant update_id
    - Actualitza l'estat de sessió i historial
    - Envia missatge a OpenAI per generar la resposta
    - Gestiona el flux d'ordre: search, confirm, order, cancel
    """
    print(f"🔄 process_update received body: {body}")
    # Desserialització del JSON
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON: {body}")
        return

    # Comprovació i deduplicació d'update_id
    update_id = data.get('update_id')
    with update_lock:
        if update_id in processed_update_ids:
            print(f"⚠️ Duplicate update_id {update_id}")
            return
        processed_update_ids.add(update_id)
    
    #Extracció de la informació del missatge i chat
    
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

    Usuari.objects.update_or_create(
        UserId=user_id,
        defaults={'FirstName': first_name, 'Username': username},
    )

    #Obtenim el nom de l'usuari per fer-lo servir a la conversa.
    first_name = Usuari.objects.get(UserId=user_id).FirstName


    # Obté text o transcriu missatge de veu
    if 'voice' in msg:
        print("🎤 Voice message detected")
        user_text = handle_voice_message(msg['voice']['file_id']) or ''
    else:
        user_text = (msg.get('text') or '').strip()
    print(f"💬 User text: {user_text}")


    #Afegir text a l'historial de la conversa
    history = conversation_history.setdefault(chat_id, [])
    
    # Gestió per a articles similars.
    if chat_id in pending_selections:
        selection = user_text.strip().lower()
        if selection in pending_selections[chat_id]:
            # Secció vàlida: assignem l'article triat
            selected_article, translated_name = pending_selections[chat_id][selection]

            ################# ARREGLO HISTORIC #########################
            print(f"\n{selected_article.DescripcionArticulo}\n")
            #history.append({"role": "user", "content": f"The article you have to put in the json is: article={selected_article.DescripcionArticulo}"})
            #history.append({"role": "user", "content": f"(admin) article={selected_article.DescripcionArticulo}"})
            #history.append({"role": "user", "content": f"i will buy: {selected_article.DescripcionArticulo}"})
            txt = translate_text("i will buy: ", ll, "en")
            print(ll)
            print(txt+str(selected_article.DescripcionArticulo))
            history.append({"role": "user", "content":txt+ " "+str(selected_article.DescripcionArticulo)})

            pending_orders[chat_id] = selected_article
            pending_selections.pop(chat_id)
        else:
            """  invalid_message = translate_text(
                "Selecció invàlida. Si us plau, tria una lletra de la llista.",
                chat_language.get(chat_id, 'en')
            ) """
            #send_telegram_message(chat_id, "posa l'accio en el JSON a: action=cancel")
            
            # Secció invàlida: provoquem una cancel·lació implícita
            history.append({"role": "user", "content": f"The action you have to put in the json is: action=cancel"})
            pending_selections.pop(chat_id)
            #return

    else:
        # Flux normal: afegim el missatge de text
        history.append({"role": "user", "content": user_text})

    # Preparar context per OpenAI (system + últims missatges)
    convo = [
        {"role": "system", "content": f"The user's name is {first_name}. Use it naturaly"},
        SYSTEM_PROMPT
    ] + history[-5:]  # Limitar a 5 missatges per reduir tokens

    # Crida al model OpenAI per obtenir resposta en format JSON
    result = call_openai(convo, response_format={"type": "json_object"})

    if not result:
        error_message = translate_text(
            "Sorry, there was an internal error. Please try again.",
            chat_language.get(chat_id, 'en')
        )
        send_telegram_message(chat_id, error_message)
        return

    # Parseig del JSON retornat
    try:
        payload = json.loads(result)
        print(f"✅ Parsed payload: {payload}")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decode error: {e}, result was: {result!r}")
        error_message = translate_message("Sorry, there was an internal error. Please try again.", chat_language.get(chat_id, 'es'))
        send_telegram_message(chat_id, error_message)
        return

    # Extracció de camps i actualització d'estat
    action = payload.get('action')
    article = payload.get('article')
    qty = payload.get('quantity')
    message = payload.get('message') 
    lang = payload.get('language', chat_language.get(chat_id, 'en'))
    chat_language[chat_id] = lang
    
    ll = lang

    # Gestió de cada acció (search, confirm, order, cancel)
    if action == 'search' and article:
        art_obj = buscar_article(article)
        print(f"Tipo de art_obj: {type(art_obj)}")
        if isinstance(art_obj, Article):
            pending_orders[chat_id] = art_obj
            unit_price = art_obj.PVP
            message += f" {translate_message('The price per unit is {unit_price}€.', lang, unit_price=unit_price)}"
        elif art_obj is None:
            error_message = translate_message("No he trobat '{article}'. Si us plau, comprova el nom o intenta amb un producte diferent.", lang, article=article)
            send_telegram_message(chat_id, error_message)
            conversation_history.pop(chat_id, None)
            return
        else:
            similar_articles = list(art_obj)
            if not similar_articles:
                error_message = translate_message("No he trobat articles similars per '{article}'.", lang, article=article)
                send_telegram_message(chat_id, error_message)
                return
            if lang != "es":
                translated_names = [translate_text(a.DescripcionArticulo, lang, 'es') for a in similar_articles]
            else:
                translated_names = [a.DescripcionArticulo for a in similar_articles ]

            pending_selections[chat_id] = {
                chr(97+i): (article, name) for i, (article, name) in enumerate(zip(similar_articles, translated_names))
            }
            options = [f"\n·🛍️{chr(97+i)}) {name}\n" for i, name in enumerate(translated_names)]
            suggestion_message = translate_message(
                "No he trobat '{article}', però aquí tens productes similars:\n{options}\nSi us plau, selecciona una lletra (a, b, c, etc.).",
                lang,
                article=article,
                options="\n".join(options)
            )
            send_telegram_message(chat_id, suggestion_message)
            return
            
    elif action == 'confirm' and chat_id in pending_orders and isinstance(qty, int):
        art_obj = pending_orders[chat_id]
        if isinstance(art_obj, Article):
            total_price = art_obj.PVP * qty
            message += f" {translate_message('Total price: {total_price}€.', lang, total_price=total_price)}"
            pending_confirmations[chat_id] = (art_obj, qty)
        else:
            error_message = translate_message("No exact article found for confirmation.", lang)
            send_telegram_message(chat_id, error_message)
            return
    elif action == 'order':
        if chat_id in pending_confirmations:
            art_obj, qty = pending_confirmations[chat_id]
            if isinstance(art_obj, Article):
                if art_obj.Unidades >= qty:
                    actualitzar_unidades(art_obj, qty)
                    generar_comanda(art_obj.CodigoArticulo, art_obj.PVP, qty, user_id)
                    total_price = art_obj.PVP * qty
                    success_message = translate_message(
                        "Your order of {qty} {article} has been placed successfully. Total price: {total_price}€. Thank you, {first_name}!",
                        lang,
                        qty=qty,
                        article=art_obj.DescripcionArticulo,
                        total_price=total_price,
                        first_name=first_name
                    )
                    send_telegram_message(chat_id, success_message)
                else:
                    out_of_stock_message = translate_message(
                        "Sorry, there is not enough stock for {article}.",
                        lang,
                        article=art_obj.DescripcionArticulo
                    )
                    send_telegram_message(chat_id, out_of_stock_message)
            else:
                error_message = translate_text("No exact article found to process the order.", lang)
                send_telegram_message(chat_id, error_message)
            pending_confirmations.pop(chat_id, None)
            pending_orders.pop(chat_id, None)
            conversation_history.pop(chat_id, None)
            chat_language.pop(chat_id, None)
            return
    elif action == 'cancel':
        cancel_message = translate_text("❌ Your order has been cancelled. ❌", lang)
        send_telegram_message(chat_id, cancel_message)
        pending_confirmations.pop(chat_id, None)
        pending_orders.pop(chat_id, None)
        conversation_history.pop(chat_id, None)
        chat_language.pop(chat_id, None)
        return

    if action in ['ask', 'search', 'confirm']:
        send_telegram_message(chat_id, message)
        history.append({"role": "assistant", "content": message})

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
        article = instance.article
        article.Unidades += instance.Quantitat
        article.save()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)