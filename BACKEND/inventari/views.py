from rest_framework import generics
from .models import Article
from .serializers import ArticleSerializer
from rest_framework.response import Response

from bot.utils import generate_embedding, pc

class ArticleListAPIView(generics.ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    #sobreescribim mètode create per poder afegir l'embedding.
    def create(self, request, *args, **kwargs):
        # Crear l'article amb la lògica estàndard
        response = super().create(request, *args, **kwargs)
        
        try:
            # Obtenir l'article creat
            article_id = response.data['CodigoArticulo']
            article = Article.objects.get(CodigoArticulo=article_id)
            
            # Generar i emmagatzemar l'embedding a Pinecone
            embedding = generate_embedding(article.DescripcionArticulo)
            index = pc.Index("sintesi")
            index.upsert([(str(article.CodigoArticulo), embedding)])
        except Exception as e:
            # Gestionar errors silenciosament (pots afegir logs si cal)
            print(f"Error afegint embedding: {e}")
        
        # Retornar la resposta original
        return response

class ArticleDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'CodigoArticulo'

    def destroy(self, request, *args, **kwargs):
        # Obtenir l'article que s'eliminarà
        article = self.get_object()
        
        # Eliminar l'article de la base de dades
        response = super().destroy(request, *args, **kwargs)
        
        try:
            # Eliminar l'embedding de Pinecone
            index = pc.Index("sintesi")
            index.delete(ids=[str(article.CodigoArticulo)])
        except Exception as e:
            # Gestionar errors silenciosament
            print(f"Error eliminant embedding: {e}")
        
        # Retornar la resposta original
        return response