from django.db import models
from inventari.models import Article

# Create your models here.
class Usuari(models.Model):
    UserId = models.IntegerField(primary_key=True)
    FirstName = models.CharField(max_length=20)
    Username = models.CharField(max_length=20, null=True, blank=True)

class Comanda(models.Model):
    ComandaId = models.AutoField(primary_key=True)
    user = models.ForeignKey(Usuari, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    Quantitat = models.IntegerField()
    PreuFinal = models.DecimalField(max_digits=10, decimal_places=2)