from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Ana sayfa (boş yol)
    path('', views.portal_anasayfa, name='portal_anasayfa'),
    
    # Giriş ve Çıkış yolları
    path('giris/', auth_views.LoginView.as_view(template_name='portal/login.html'), name='giris'),
    path('cikis/', auth_views.LogoutView.as_view(next_page='/'), name='cikis'),
]