# randevu/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.functions import TruncDate

class Firma(models.Model):
    ad = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.ad

    class Meta:
        verbose_name = "Firma"
        verbose_name_plural = "Firmalar"


class TemsilciProfili(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefon = models.CharField(max_length=15, blank=True)
    firma = models.ForeignKey(Firma, on_delete=models.SET_NULL, null=True, blank=True)
    ozel_gun_notu = models.CharField(max_length=255, blank=True, help_text="Doğum günü, evlilik yıldönümü gibi hatırlatıcı notlar.")
    sorumlu_oldugu_urunler = models.ManyToManyField(
        'Urun',
        blank=True,
        verbose_name="Sorumlu Olduğu Ürünler"
    )

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    class Meta:
        verbose_name = "Temsilci Profili"
        verbose_name_plural = "Temsilci Profilleri"


class Randevu(models.Model):
    STATUS_SECENEKLERI = (
        ('beklemede', 'Beklemede'),
        ('onaylandi', 'Onaylandı'),
        ('gelinmedi', 'Gelinmedi'),
        ('tamamlandi', 'Tamamlandı'),
    )
    temsilci = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    tarih_saat = models.DateTimeField(unique=True)  # tek slot tek bir andır
    status = models.CharField(max_length=10, choices=STATUS_SECENEKLERI, default='beklemede')
    notlar = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['tarih_saat']
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"
        constraints = [
            # Aynı temsilci aynı GÜN içinde sadece 1 randevu alabilsin (temsilci boş değilken)
            models.UniqueConstraint(
                TruncDate('tarih_saat'),
                'temsilci',
                name='uniq_temsilci_per_day',
                condition=Q(temsilci__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=['tarih_saat']),
        ]

    def __str__(self):
        if self.temsilci:
            return f"{self.tarih_saat.strftime('%d-%m-%Y %H:%M')} - {self.temsilci.first_name}"
        else:
            return f"{self.tarih_saat.strftime('%d-%m-%Y %H:%M')} - (BOŞ RANDEVU)"


class Urun(models.Model):
    firma = models.ForeignKey(Firma, on_delete=models.CASCADE, related_name='urunler')
    ad = models.CharField(max_length=255)
    aciklama = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['ad']
        unique_together = ('firma', 'ad')
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

    def __str__(self):
        return self.ad


class Teklif(models.Model):
    randevu = models.ForeignKey(Randevu, on_delete=models.CASCADE, related_name='teklifler')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE)
    mal_fazlasi_sarti = models.CharField(max_length=255, blank=True, verbose_name="Mal Fazlası Şartı (Örn: 10+1, 20+3)")
    ekstra_iskonto = models.CharField(max_length=255, blank=True, verbose_name="Ekstra İskonto (Örn: Fatura altı %3, Nakit çek)")
    eczaci_degerlendirmesi = models.TextField(blank=True, verbose_name="Eczacı Değerlendirmesi")

    class Meta:
        ordering = ['-id']
        verbose_name = "Teklif"
        verbose_name_plural = "Teklifler"

    def __str__(self):
        return f"{self.randevu.tarih_saat.strftime('%d-%m-%Y')} - {self.urun.ad} Teklifi"
