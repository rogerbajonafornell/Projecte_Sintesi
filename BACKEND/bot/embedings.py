import os
import sys
import django
from pinecone import Pinecone
from dotenv import load_dotenv

# Afegir el directori del projecte al PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Configurar l'entorn de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

# Ara pots importar models
from inventari.models import Article
from utils import generate_embedding

# Carregar variables d'entorn
load_dotenv()

# Configuració de Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "sintesi"  # Nom de l'índex que has creat a Pinecone

# Connectar a l'índex
index = pc.Index(INDEX_NAME)

# Emmagatzemar embeddings per a tots els articles
for art in Article.objects.all():
    try:
        # Generar embedding per al nom de l’article
        embedding = generate_embedding(art.DescripcionArticulo)
        
        # Emmagatzemar l’embedding a Pinecone amb l’ID de l’article
        index.upsert([(str(art.CodigoArticulo), embedding)])
        
        print(f"✅ Embedding emmagatzemat per a l’article: {art.DescripcionArticulo}")
    except Exception as e:
        print(f"❌ Error emmagatzemant l’article {art.DescripcionArticulo}: {e}")

print("🎉 Tots els embeddings han estat emmagatzemats a Pinecone!")