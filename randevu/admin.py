from django.contrib import admin

from .models import Firma, TemsilciProfili, Randevu, Urun, Teklif

admin.site.register(Firma)
admin.site.register(TemsilciProfili)
admin.site.register(Randevu)
admin.site.register(Urun)
admin.site.register(Teklif)