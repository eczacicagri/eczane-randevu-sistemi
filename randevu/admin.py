# randevu/admin.py

from django.contrib import admin
from .models import Firma, TemsilciProfili, Randevu

# Modellerimizi admin paneline kaydediyoruz.
admin.site.register(Firma)
admin.site.register(TemsilciProfili)
admin.site.register(Randevu)