from rest_framework import serializers
from .models import Usuari, Comanda
from inventari.serializers import ArticleSerializer

class UsuariSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuari
        fields = '__all__'

class ComandaSerializer(serializers.ModelSerializer):
    Article = ArticleSerializer(source='article', read_only=True)
    User = UsuariSerializer(source='user', read_only=True)

    class Meta:
        model = Comanda
        fields = ['ComandaId', 'Quantitat', 'PreuFinal', 'Article', 'User']