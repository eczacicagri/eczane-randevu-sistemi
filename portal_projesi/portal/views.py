from django.shortcuts import render

def portal_anasayfa(request):
    if request.user.is_authenticated:
        # Kullanıcı giriş yapmışsa, ona uygulama linklerini gösteren dashboard'ı göster
        return render(request, 'portal/dashboard.html')
    else:
        # Kullanıcı giriş yapmamışsa, onu giriş butonunun olduğu karşılama sayfasına yönlendir
        return render(request, 'portal/landing_page.html')