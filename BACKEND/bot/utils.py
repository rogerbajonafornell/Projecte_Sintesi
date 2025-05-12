#import openai
#import pinecone
#import os
# Configuració d'OpenAI
# openai.api_key = os.getenv("OPENAI_API_KEY")

# # Configuració de Pinecone
# pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENV"))
# INDEX_NAME = "articles"  # Nom de l'índex a Pinecone, assegura't que existeixi

# def generate_embedding(text):
#     """Genera un embedding per a un text donat utilitzant OpenAI."""
#     response = openai.Embedding.create(
#         input=text,
#         model="text-embedding-3-small"
#     )
#     return response['data'][0]['embedding']

# def search_similar_articles(query, top_k=5):
#     """Cerca articles similars a Pinecone utilitzant l'embedding de la consulta."""
#     query_embedding = generate_embedding(query)
#     index = pinecone.Index(INDEX_NAME)
#     results = index.query(vector=query_embedding, top_k=top_k, include_values=False)
#     return [int(match.id) for match in results.matches]