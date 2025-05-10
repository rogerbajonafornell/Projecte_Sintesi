from django.urls import path
from .views import UsuariListAPIView, ComandaListAPIView, ComandaDetailAPIView

urlpatterns = [
    path('usuaris/', UsuariListAPIView.as_view()),
    path('comandes/', ComandaListAPIView.as_view()),
    path('comandes/<int:ComandaId>/', ComandaDetailAPIView.as_view()),

]