from django.db import models

# Create your models here.
class Article(models.Model):
   CodigoArticulo = models.AutoField(primary_key=True)
   DescripcionArticulo = models.CharField(max_length=100)
   PVP = models.DecimalField(max_digits=10, decimal_places=2)
   Unidades = models.IntegerField()
