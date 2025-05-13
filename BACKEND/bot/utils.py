import os
import openai
from pinecone import Pinecone
from dotenv import load_dotenv

# Carregar variables d'entorn
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuració de Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "sintesi"

def generate_embedding(text: str) -> list[float]:
    """Genera un embedding per al text amb el nou endpoint embeddings.create."""
    resp = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    # La resposta porta una llista resp.data amb elements que contenen .embedding
    return resp.data[0].embedding

def search_similar_articles(query: str, top_k: int = 5) -> list[int]:
    """Cerca articles similars a Pinecone utilitzant l'embedding de la query."""
    query_embedding = generate_embedding(query)
    index = pc.Index(INDEX_NAME)
    # Fes la consulta a Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_values=False  # només cal el match.id
    )
    return [int(match.id) for match in results.matches]

if __name__ == "__main__":
    # Exemple d’ús
    similar_ids = search_similar_articles("Un text de prova per cercar similars")
    print("Articles similars (IDs):", similar_ids)
