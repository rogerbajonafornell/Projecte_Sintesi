import os
import openai
from pinecone import Pinecone
from dotenv import load_dotenv

# --- Carregar .env i configurar OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Inicialitzar Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("sintesi")

def generate_embedding(text: str) -> list[float]:
    """Genera embedding amb la nova API d'OpenAI."""
    resp = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return resp.data[0].embedding

def search_similar_articles(query: str, top_k: int = 5) -> list[int]:
    """Cerca similars a Pinecone."""
    emb = generate_embedding(query)
    results = index.query(
        vector=emb,
        top_k=top_k,
        include_values=False
    )
    return [int(m.id) for m in results.matches]

if __name__ == "__main__":
    print("Similars:", search_similar_articles("Exemple de cerca"))
