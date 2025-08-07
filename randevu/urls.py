from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Ana Sayfa ve Kullanıcı İşlemleri
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('kayit/', views.kayit_ol, name='kayit_ol'),
    path('giris/', auth_views.LoginView.as_view(template_name='randevu/giris.html'), name='giris'),
    path('cikis/', auth_views.LogoutView.as_view(next_page='ana_sayfa'), name='cikis'),
    path('profil/', views.profil_guncelle, name='profil_guncelle'),

    # Randevu İşlemleri
    path('randevular/', views.randevu_listesi, name='randevu_listesi'),
    path('randevularim/', views.my_randevular, name='my_randevular'),
    path('randevu/al/<int:randevu_id>/', views.randevu_al, name='randevu_al'),
    path('randevu/iptal/<int:randevu_id>/', views.randevu_iptal, name='randevu_iptal'),

    # Yönetim (Admin) İşlemleri
    path('yonetim/toplu-randevu/', views.toplu_randevu_olustur, name='toplu_randevu_olustur'),
]