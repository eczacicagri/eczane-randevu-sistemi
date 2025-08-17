from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Ana sayfaya (boş yol) gelen istekleri portal.urls'e gönder
    path('', include('portal.urls')), 
]