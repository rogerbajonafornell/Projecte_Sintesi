from django.urls import path
from .views import ArticleListAPIView, ArticleDetailAPIView

urlpatterns = [
    path('articles/', ArticleListAPIView.as_view()),
    path('articles/<int:CodigoArticulo>/', ArticleDetailAPIView.as_view()),
]
