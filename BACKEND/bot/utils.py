import os
from functools import reduce
from operator import or_
from django.db.models import Q, Case, When, IntegerField, Value
from dotenv import load_dotenv
import openai
from pinecone import Pinecone
from inventari.models import Article

# Carregar .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicialitzar Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("sintesi")

def generate_embedding(text: str) -> list[float]:
    """Genera embedding amb l'API d'OpenAI."""
    resp = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return resp.data[0].embedding



def search_similar_articles(key_es: str, top_k: int = 5) -> list[int]:
    """
    Retorna exactament top_k articles ordenats per rellevància combinant:
    1) coincidències literals (paraules clau) ordenades per nombre de coincidències,
    després 2) embeddings semàntics ordenats per score.
    Sempre es retornen top_k IDs.
    """
    # 1. Cercar per paraula clau a la base de dades
    keywords = [kw.strip().lower() for kw in key_es.split() if kw.strip()]
    literal_ids = []
    if keywords:
        conditions = [Q(DescripcionArticulo__icontains=kw) for kw in keywords]
        qs = (
            Article.objects
                   .annotate(
                       matchCount=reduce(
                           lambda acc, kw: acc + Case(
                               When(DescripcionArticulo__icontains=kw, then=Value(1)),
                               default=Value(0), output_field=IntegerField()
                           ), keywords, Value(0)
                       )
                   )
                   .filter(reduce(or_, conditions))
                   .order_by('-matchCount')
        )
        literal_ids = list(qs.values_list('pk', flat=True))

    # 2. Cercar per embeddings semàntics
    emb = generate_embedding(key_es)
    raw = index.query(
        vector=emb,
        top_k=top_k * 3,
        include_values=False
    )
    semantic_sorted = [int(m.id) for m in sorted(raw.matches, key=lambda m: m.score, reverse=True)]

    # 3. Combina literals i semàntics, evitant duplicats
    combined = []
    # Afegir literals primer
    for id_ in literal_ids:
        if id_ not in combined:
            combined.append(id_)
        if len(combined) >= top_k:
            break
    # Afegir semàntics després
    for id_ in semantic_sorted:
        if len(combined) >= top_k:
            break
        if id_ not in combined:
            combined.append(id_)

    return combined[:top_k]


