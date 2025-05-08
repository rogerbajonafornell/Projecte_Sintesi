from django.urls import path
from .views import UsuariListAPIView, ComandaListAPIView 

urlpatterns = [
    path('usuaris/', UsuariListAPIView.as_view()),
    path('comandes/', ComandaListAPIView.as_view()),
]