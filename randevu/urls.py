# randevu/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Ana Sayfa ve Kullanıcı İşlemleri
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('kayit/', views.kayit_ol, name='kayit_ol'),
    path('giris/', auth_views.LoginView.as_view(template_name='randevu/giris.html'), name='giris'),
    path('cikis/', auth_views.LogoutView.as_view(next_page='https://www.portecza.com/'), name='cikis'),
    path('profil/', views.profil_guncelle, name='profil_guncelle'),

    # Randevu İşlemleri
    path('randevular/', views.randevu_listesi, name='randevu_listesi'),
    path('randevularim/', views.my_randevular, name='my_randevular'),
    path('randevu/al/<int:randevu_id>/', views.randevu_al, name='randevu_al'),
    path('randevu/iptal/<int:randevu_id>/', views.randevu_iptal, name='randevu_iptal'),
    path('randevu/detay/<int:randevu_id>/', views.randevu_detay, name='randevu_detay'),

    # Yönetim (Admin) İşlemleri
    path('yonetim/panel/', views.yonetim_paneli, name='yonetim_paneli'),
    path('yonetim/onayla/<int:randevu_id>/', views.yonetim_randevu_onayla, name='yonetim_randevu_onayla'),
    path('yonetim/iptal/<int:randevu_id>/', views.yonetim_randevu_iptal, name='yonetim_randevu_iptal'),
    path('yonetim/tamamla/<int:randevu_id>/', views.yonetim_randevu_tamamla, name='yonetim_randevu_tamamla'),
    path('yonetim/toplu-randevu/', views.toplu_randevu_olustur, name='toplu_randevu_olustur'),
    path('yonetim/toplu-firma-yukle/', views.toplu_firma_yukle, name='toplu_firma_yukle'),
    path('yonetim/toplu-urun-yukle/', views.toplu_urun_yukle, name='toplu_urun_yukle'),

    # Boş randevular (Admin)
    path('yonetim/bos-randevular/', views.yonetim_bos_randevular, name='yonetim_bos_randevular'),
    path('yonetim/sil/<int:randevu_id>/', views.yonetim_randevu_sil, name='yonetim_randevu_sil'),

    # Örnek CSV'ler
    path('yonetim/ornek-firma-csv/', views.ornek_firma_csv, name='ornek_firma_csv'),
    path('yonetim/ornek-urun-csv/', views.ornek_urun_csv, name='ornek_urun_csv'),

    # YENİ: Boş slot toplu sil (tarih aralığı)
    path('yonetim/bos-toplu-sil/', views.yonetim_bos_toplu_sil, name='yonetim_bos_toplu_sil'),
    # Çağrı ekledi: randevu gelinmedi urls kodu
    path('yonetim/gelinmedi/<int:randevu_id>/', views.yonetim_randevu_gelinmedi, name='yonetim_randevu_gelinmedi'),
    path('yonetim/toplu-randevu/', views.toplu_randevu_olustur, name='toplu_randevu_olustur'),
    # YENİ: Raporlar
    path('yonetim/raporlar/', views.yonetim_raporlar, name='yonetim_raporlar'),
]
