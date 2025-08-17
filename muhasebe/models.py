from django.db import models
from django.conf import settings

# Not: Diğer uygulamanızdaki 'Firma' modeline bir çakışma olmaması için
# buradaki cari hesapları 'Cari' olarak adlandırıyoruz.
class Cari(models.Model):
    TIP_SECENEKLERI = (
        ('Musteri', 'Müşteri'),
        ('Tedarikci', 'Tedarikçi'),
        ('Diger', 'Diğer'),
    )
    unvan = models.CharField(max_length=255, verbose_name="Ünvan")
    vergi_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="Vergi No")
    vergi_dairesi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vergi Dairesi")
    adres = models.TextField(blank=True, null=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    eposta = models.EmailField(blank=True, null=True)
    bakiye = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tip = models.CharField(max_length=10, choices=TIP_SECENEKLERI, default='Diger')

    def __str__(self):
        return self.unvan

    class Meta:
        verbose_name = "Cari Hesap"
        verbose_name_plural = "Cari Hesaplar"

class Kategori(models.Model):
    kategori_adi = models.CharField(max_length=100, unique=True, verbose_name="Kategori Adı")

    def __str__(self):
        return self.kategori_adi

    class Meta:
        verbose_name = "Ürün Kategorisi"
        verbose_name_plural = "Ürün Kategorileri"

class Fatura(models.Model):
    fatura_no = models.CharField(max_length=50, verbose_name="Fatura Numarası")
    cari = models.ForeignKey(Cari, on_delete=models.SET_NULL, null=True, blank=True)
    tarih = models.DateField()
    tip = models.CharField(max_length=20, verbose_name="Fatura Tipi") # Alış/Satış
    ara_toplam = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    kdv_toplam = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    genel_toplam = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    odeme_durumu = models.CharField(max_length=20, default="Ödenmedi")
    efatura_uuid = models.CharField(max_length=100, blank=True, null=True)
    efatura_durum = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.fatura_no} - {self.cari.unvan if self.cari else 'Cari Yok'}"

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturalar"
        ordering = ['-tarih']

# Not: Randevu sistemindeki 'Urun' modeli ile çakışmaması için 'MuhasebeUrun' olarak adlandırıldı.
class MuhasebeUrun(models.Model):
    barkod = models.CharField(max_length=100, unique=True)
    urun_adi = models.CharField(max_length=255, verbose_name="Ürün Adı")
    kategori = models.ForeignKey(Kategori, on_delete=models.SET_NULL, null=True, blank=True)
    birim = models.CharField(max_length=20, default="Adet")
    kdv_orani = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    alis_fiyati = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    satis_fiyati = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stok_miktari = models.IntegerField(default=0)

    def __str__(self):
        return self.urun_adi

    class Meta:
        verbose_name = "Muhasebe Ürünü"
        verbose_name_plural = "Muhasebe Ürünleri"

class StokHareketi(models.Model):
    urun = models.ForeignKey(MuhasebeUrun, on_delete=models.CASCADE)
    fatura = models.ForeignKey(Fatura, on_delete=models.SET_NULL, null=True, blank=True)
    tarih = models.DateTimeField(auto_now_add=True)
    tip = models.CharField(max_length=10, verbose_name="Hareket Tipi") # Giriş/Çıkış
    miktar = models.IntegerField()
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.urun.urun_adi} - {self.tip} ({self.miktar})"

    class Meta:
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"
        ordering = ['-tarih']

class Odeme(models.Model):
    cari = models.ForeignKey(Cari, on_delete=models.CASCADE)
    tarih = models.DateField()
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    islem_tipi = models.CharField(max_length=20) # Tahsilat/Ödeme
    odeme_yontemi = models.CharField(max_length=50) # Nakit/Kredi Kartı
    aciklama = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.cari.unvan} - {self.tutar} TL {self.islem_tipi}"

    class Meta:
        verbose_name = "Ödeme"
        verbose_name_plural = "Ödemeler"

class GunlukOzet(models.Model):
    tarih = models.DateField(unique=True)
    baslangic_tutari = models.DecimalField(max_digits=10, decimal_places=2)
    sistem_nakit_geliri = models.DecimalField(max_digits=10, decimal_places=2)
    kasadan_cikis_toplami = models.DecimalField(max_digits=10, decimal_places=2)
    beklenen_nakit = models.DecimalField(max_digits=10, decimal_places=2)
    sayilan_nakit = models.DecimalField(max_digits=10, decimal_places=2)
    fark = models.DecimalField(max_digits=10, decimal_places=2)
    durum = models.CharField(max_length=20, blank=True, null=True)
    aciklama = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tarih.strftime('%d-%m-%Y')} Kasa Özeti"

    class Meta:
        verbose_name = "Günlük Kasa Özeti"
        verbose_name_plural = "Günlük Kasa Özetleri"