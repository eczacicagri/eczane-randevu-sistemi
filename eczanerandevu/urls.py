# eczanerandevu/urls.py

from django.contrib import admin
from django.urls import path, include # include'ü ekledik

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('randevu.urls')), # randevu uygulamasının URL'lerini dahil et
]