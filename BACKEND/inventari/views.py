from rest_framework import generics
from .models import Article
from .serializers import ArticleSerializer

class ArticleListAPIView(generics.ListAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

