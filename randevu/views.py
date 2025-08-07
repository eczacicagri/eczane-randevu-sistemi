# randevu/views.py (TAM VE GÜNCEL HALİ)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from datetime import datetime, timedelta
from .forms import KayitFormu, TemsilciProfiliFormu, TopluRandevuFormu
from .models import Randevu

def ana_sayfa(request):
    return render(request, 'randevu/ana_sayfa.html')

def kayit_ol(request):
    if request.method == 'POST':
        form = KayitFormu(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data.get('password'))
            user.save()
            login(request, user)
            return redirect('ana_sayfa')
    else:
        form = KayitFormu()
    return render(request, 'randevu/kayit_ol.html', {'form': form})

@login_required
def profil_guncelle(request):
    if request.method == 'POST':
        form = TemsilciProfiliFormu(request.POST, instance=request.user.temsilciprofili)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profiliniz başarıyla güncellendi!')
            return redirect('profil_guncelle')
    else:
        form = TemsilciProfiliFormu(instance=request.user.temsilciprofili)
    context = {'form': form}
    return render(request, 'randevu/profil.html', context)

@login_required
def randevu_listesi(request):
    bos_randevular = Randevu.objects.filter(temsilci__isnull=True).order_by('tarih_saat')
    context = {'randevular': bos_randevular}
    return render(request, 'randevu/randevu_listesi.html', context)

@login_required
def my_randevular(request):
    alinan_randevular = Randevu.objects.filter(temsilci=request.user).order_by('tarih_saat')
    context = {'randevular': alinan_randevular}
    return render(request, 'randevu/my_randevular.html', context)

@login_required
def randevu_al(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if request.method == 'POST':
        if randevu.temsilci is None:
            randevu.temsilci = request.user
            randevu.save()
            return redirect('my_randevular')
        else:
            return redirect('ana_sayfa')
    return redirect('randevu_listesi')

@login_required
def randevu_iptal(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if randevu.temsilci == request.user:
        if request.method == 'POST':
            randevu.temsilci = None
            randevu.save()
            return redirect('my_randevular')
    return redirect('ana_sayfa')

# --- HATAYA SEBEP OLAN EKSİK FONKSİYON ---
@login_required
@user_passes_test(lambda u: u.is_superuser) # Sadece süper kullanıcılar erişebilir
def toplu_randevu_olustur(request):
    if request.method == 'POST':
        form = TopluRandevuFormu(request.POST)
        if form.is_valid():
            tarih = form.cleaned_data['tarih']
            baslangic_saati = form.cleaned_data['baslangic_saati']
            bitis_saati = form.cleaned_data['bitis_saati']
            aralik = form.cleaned_data['aralik']

            mevcut_saat = datetime.combine(tarih, baslangic_saati)
            bitis_dt = datetime.combine(tarih, bitis_saati)

            olusturulan_sayisi = 0
            while mevcut_saat < bitis_dt:
                randevu, olusturuldu = Randevu.objects.get_or_create(tarih_saat=mevcut_saat)
                if olusturuldu:
                    olusturulan_sayisi += 1

                mevcut_saat += timedelta(minutes=aralik)

            messages.success(request, f'{olusturulan_sayisi} adet yeni randevu slotu başarıyla oluşturuldu.')
            return redirect('toplu_randevu_olustur')
    else:
        form = TopluRandevuFormu()

    context = {'form': form}
    return render(request, 'randevu/toplu_randevu_olustur.html', context)