from django.db import models

# Create your models here.
class Usuari(models.Model):
    UserId = models.IntegerField(primary_key=True)
    FirstName = models.CharField(max_length=20)
    Username = models.CharField(max_length=20)
