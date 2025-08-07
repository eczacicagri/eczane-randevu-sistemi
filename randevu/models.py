# randevu/models.py (TAM VE GÜNCEL HALİ)

from django.db import models
from django.contrib.auth.models import User

class Firma(models.Model):
    ad = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.ad

class TemsilciProfili(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefon = models.CharField(max_length=15, blank=True)
    firma = models.ForeignKey(Firma, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.firma.ad if self.firma else 'Firma Belirtilmemiş'})"

class Randevu(models.Model):
    # --- ARADIĞINIZ VE GÜNCELLEDİĞİMİZ SATIR BURADA ---
    temsilci = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    tarih_saat = models.DateTimeField()
    notlar = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('tarih_saat',)
        ordering = ['tarih_saat'] 

    def __str__(self):
        # Bu fonksiyon, randevunun sahibi varsa ismini, yoksa "BOŞ RANDEVU" yazar.
        if self.temsilci:
            return f"{self.tarih_saat.strftime('%d-%m-%Y %H:%M')} - {self.temsilci.first_name} {self.temsilci.last_name}"
        else:
            return f"{self.tarih_saat.strftime('%d-%m-%Y %H:%M')} - (BOŞ RANDEVU)"