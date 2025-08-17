# randevu/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
import csv
import io

from .forms import KayitFormu, TemsilciProfiliFormu, TopluRandevuFormu, TeklifFormu
from .models import Randevu, Firma, Urun, Teklif


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
    qs = Randevu.objects.filter(temsilci__isnull=True).order_by('tarih_saat')

    # tarih filtreleri (YYYY-MM-DD)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(tarih_saat__date__gte=start)
    if end:
        qs = qs.filter(tarih_saat__date__lte=end)

    paginator = Paginator(qs, 20)  # sayfa başına 20 slot
    page = request.GET.get('page')
    randevular = paginator.get_page(page)

    context = {'randevular': randevular, 'start': start or '', 'end': end or ''}
    return render(request, 'randevu/randevu_listesi.html', context)


@login_required
def my_randevular(request):
    alinan_randevular = Randevu.objects.filter(temsilci=request.user).order_by('tarih_saat')
    context = {'randevular': alinan_randevular}
    return render(request, 'randevu/my_randevular.html', context)


@login_required
def randevu_al(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)

    # Geçmiş randevu engeli
    if randevu.tarih_saat < timezone.now():
        messages.error(request, 'Geçmiş tarihli randevu alınamaz.')
        return redirect('randevu_listesi')

    if request.method == 'POST':
        randevu_gunu = randevu.tarih_saat.date()
        ayni_gun_randevu_var_mi = Randevu.objects.filter(
            temsilci=request.user,
            tarih_saat__date=randevu_gunu
        ).exists()
        if ayni_gun_randevu_var_mi:
            messages.error(request, f"{randevu_gunu.strftime('%d-%m-%Y')} tarihi için zaten bir randevunuz var.")
            return redirect('randevu_listesi')

        if randevu.temsilci is None:
            randevu.temsilci = request.user
            randevu.status = 'beklemede'
            randevu.save()
            messages.success(request, f"{randevu.tarih_saat.strftime('%d-%m-%Y %H:%M')} için talebiniz alındı. Onay bekleniyor.")
            return redirect('my_randevular')
        else:
            messages.warning(request, 'Üzgünüz, bu randevu sizden hemen önce başka bir temsilci tarafından alındı.')
            return redirect('randevu_listesi')
    return redirect('randevu_listesi')


@login_required
def randevu_iptal(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if randevu.temsilci == request.user and request.method == 'POST':
        randevu.temsilci = None
        randevu.status = 'beklemede'
        randevu.save()
        messages.success(request, 'Randevunuz iptal edildi ve slot tekrar boşa alındı.')
        return redirect('my_randevular')
    return redirect('ana_sayfa')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_paneli(request):
    """
    DOLU randevuların yönetim paneli.
    YENİ: temsilci adı ve firma adına göre arama/filtre eklendi.
    """
    qs = Randevu.objects.filter(temsilci__isnull=False).order_by('tarih_saat')

    durum = request.GET.get('durum')  # beklemede/onaylandi/gelinmedi/tamamlandi
    start = request.GET.get('start')
    end = request.GET.get('end')
    q_temsilci = request.GET.get('q_temsilci', '').strip()
    q_firma = request.GET.get('q_firma', '').strip()

    if durum:
        qs = qs.filter(status=durum)
    if start:
        qs = qs.filter(tarih_saat__date__gte=start)
    if end:
        qs = qs.filter(tarih_saat__date__lte=end)
    if q_temsilci:
        # ad/soyad/username içinde arama
        qs = qs.filter(
            Q(temsilci__first_name__icontains=q_temsilci) |
            Q(temsilci__last_name__icontains=q_temsilci) |
            Q(temsilci__username__icontains=q_temsilci)
        )
    if q_firma:
        qs = qs.filter(temsilci__temsilciprofili__firma__ad__icontains=q_firma)

    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    randevular = paginator.get_page(page)

    context = {
        'randevular': randevular,
        'durum': durum or '',
        'start': start or '',
        'end': end or '',
        'q_temsilci': q_temsilci,
        'q_firma': q_firma,
    }
    return render(request, 'randevu/yonetim_paneli.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_randevu_onayla(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if randevu.status != 'beklemede':
        messages.error(request, 'Sadece "Beklemede" durumundaki randevular onaylanabilir.')
        return redirect('yonetim_paneli')
    randevu.status = 'onaylandi'
    randevu.save()
    messages.success(request, 'Randevu başarıyla onaylandı.')
    return redirect('yonetim_paneli')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_randevu_iptal(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if randevu.status not in ('beklemede', 'onaylandi'):
        messages.error(request, 'Bu randevu mevcut durumunda iptal edilemez.')
        return redirect('yonetim_paneli')
    randevu.temsilci = None
    randevu.status = 'beklemede'
    randevu.save()
    messages.warning(request, 'Randevu iptal edildi ve slot tekrar boşa alındı.')
    return redirect('yonetim_paneli')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toplu_randevu_olustur(request):
    if request.method == 'POST':
        form = TopluRandevuFormu(request.POST)
        if form.is_valid():
            tarih = form.cleaned_data['tarih']
            baslangic_saati = form.cleaned_data['baslangic_saati']
            bitis_saati = form.cleaned_data['bitis_saati']
            aralik = form.cleaned_data['aralik']

            tz = timezone.get_current_timezone()
            mevcut_saat = datetime.combine(tarih, baslangic_saati)
            if timezone.is_naive(mevcut_saat):
                mevcut_saat = timezone.make_aware(mevcut_saat, tz)
            bitis_dt = datetime.combine(tarih, bitis_saati)
            if timezone.is_naive(bitis_dt):
                bitis_dt = timezone.make_aware(bitis_dt, tz)

            now = timezone.now()
            olusturulan_sayisi = 0
            while mevcut_saat < bitis_dt:
                if mevcut_saat >= now:
                    _, olusturuldu = Randevu.objects.get_or_create(tarih_saat=mevcut_saat)
                    if olusturuldu:
                        olusturulan_sayisi += 1
                mevcut_saat += timedelta(minutes=aralik)

            messages.success(request, f'{olusturulan_sayisi} adet yeni randevu slotu oluşturuldu (geçmiş saatler atlandı).')
            return redirect('toplu_randevu_olustur')
    else:
        form = TopluRandevuFormu()
    context = {'form': form}
    return render(request, 'randevu/toplu_randevu_olustur.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toplu_firma_yukle(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Hata: Lütfen .csv uzantılı bir dosya yükleyin.')
            return redirect('toplu_firma_yukle')
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            next(io_string, None)  # başlık satırını atla
            reader = csv.reader(io_string, delimiter=',')
            eklenen_sayisi = 0
            mevcut_sayisi = 0
            for row in reader:
                firma_adi = (row[0] or '').strip() if row else ''
                if firma_adi:
                    _, olusturuldu = Firma.objects.get_or_create(ad=firma_adi)
                    if olusturuldu:
                        eklenen_sayisi += 1
                    else:
                        mevcut_sayisi += 1
            messages.success(request, f'İşlem tamamlandı. {eklenen_sayisi} yeni firma eklendi, {mevcut_sayisi} firma zaten mevcuttu.')
        except Exception as e:
            messages.error(request, f'Dosya okunurken bir hata oluştu: {e}')
        return redirect('toplu_firma_yukle')
    return render(request, 'randevu/toplu_firma_yukle.html')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toplu_urun_yukle(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Hata: Lütfen .csv uzantılı bir dosya yükleyin.')
            return redirect('toplu_urun_yukle')
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            next(io_string, None)  # başlık satırını atla
            reader = csv.reader(io_string, delimiter=',')
            eklenen_sayisi = 0
            mevcut_sayisi = 0
            hatalar = []
            for row in reader:
                try:
                    firma_adi = (row[0] or '').strip()
                    urun_adi = (row[1] or '').strip()
                    barkod = (row[2] or '').strip()
                    if not all([firma_adi, urun_adi, barkod]):
                        hatalar.append(f"Satır atlandı (boş hücre var): {row}")
                        continue
                    firma, _ = Firma.objects.get_or_create(ad=firma_adi)
                    # basit varyant: barkod'u modelde alan olarak kullanmıyoruz
                    _, olusturuldu = Urun.objects.get_or_create(
                        firma=firma,
                        ad=urun_adi,
                    )
                    if olusturuldu:
                        eklenen_sayisi += 1
                    else:
                        mevcut_sayisi += 1
                except IndexError:
                    hatalar.append(f"Satır atlandı (eksik sütun var): {row}")
            mesaj = f'İşlem tamamlandı. {eklenen_sayisi} yeni ürün eklendi, {mevcut_sayisi} ürün zaten mevcuttu.'
            if hatalar:
                mesaj += f" {len(hatalar)} satırda hata oluştu."
            messages.success(request, mesaj)
        except Exception as e:
            messages.error(request, f'Dosya okunurken bir hata oluştu: {e}')
        return redirect('toplu_urun_yukle')
    return render(request, 'randevu/toplu_urun_yukle.html')


@login_required
def randevu_detay(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    teklifler = randevu.teklifler.all()

    if not (request.user == randevu.temsilci or request.user.is_superuser):
        return redirect('ana_sayfa')

    if request.method == 'POST':
        form = TeklifFormu(request.POST, user=randevu.temsilci)
        if form.is_valid():
            yeni_teklif = form.save(commit=False)
            yeni_teklif.randevu = randevu
            yeni_teklif.save()
            messages.success(request, 'Yeni teklif başarıyla eklendi.')
            return redirect('randevu_detay', randevu_id=randevu.id)
    else:
        form = TeklifFormu(user=randevu.temsilci)

    context = {'randevu': randevu, 'teklifler': teklifler, 'form': form}
    return render(request, 'randevu/randevu_detay.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_randevu_tamamla(request, randevu_id):
    randevu = get_object_or_404(Randevu, id=randevu_id)
    if randevu.status != 'onaylandi':
        messages.error(request, 'Sadece "Onaylandı" durumundaki randevular tamamlanabilir.')
        return redirect('yonetim_paneli')
    randevu.status = 'tamamlandi'
    randevu.save()
    messages.success(request, 'Randevu "Tamamlandı" olarak işaretlendi.')
    return redirect('yonetim_paneli')


# Örnek CSV endpoint'leri


from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse

@user_passes_test(lambda u: u.is_superuser)
def ornek_firma_csv(request):
    content = "Firma Adları\nACME\nUmbrella\nGlobex\n"
    resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="ornek_firma_listesi.csv"'
    return resp

@user_passes_test(lambda u: u.is_superuser)
def ornek_urun_csv(request):
    content = "Firma Adı,Ürün Adı,Barkod\nACME,Vitamin C 1000,1234567890123\nUmbrella,Omega 3,9876543210123\n"
    resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="ornek_urun_listesi.csv"'
    return resp



# --- Boş randevuları listele (Admin) ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_bos_randevular(request):
    qs = Randevu.objects.filter(temsilci__isnull=True).order_by('tarih_saat')

    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(tarih_saat__date__gte=start)
    if end:
        qs = qs.filter(tarih_saat__date__lte=end)

    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    randevular = paginator.get_page(page)

    context = {'randevular': randevular, 'start': start or '', 'end': end or ''}
    return render(request, 'randevu/yonetim_bos_randevular.html', context)


# --- Boş randevu tekil sil (Admin) ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def yonetim_randevu_sil(request, randevu_id):
    r = get_object_or_404(Randevu, id=randevu_id)
    if r.temsilci is not None:
        messages.error(request, 'Bu randevu dolu; silinemez. Önce iptal edip boşa alın.')
        return redirect('yonetim_bos_randevular')
    r.delete()
    messages.success(request, 'Boş randevu slotu silindi.')
    return redirect('yonetim_bos_randevular')


# --- YENİ: Boş randevuları tarih aralığına göre TOPLU sil (Admin) ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_bos_toplu_sil(request):
    """
    GET: form, aralıkta kaç boş slot var gösterir
    POST: belirtilen aralıktaki boş slotları topluca siler
    """
    silinen = None
    sayi = None
    start = request.GET.get('start') or request.POST.get('start') or ''
    end = request.GET.get('end') or request.POST.get('end') or ''

    qs = Randevu.objects.filter(temsilci__isnull=True)
    if start:
        qs = qs.filter(tarih_saat__date__gte=start)
    if end:
        qs = qs.filter(tarih_saat__date__lte=end)

    if request.method == 'POST':
        sayi = qs.count()
        silinen = sayi
        qs.delete()
        messages.success(request, f'Seçilen aralıkta {silinen} boş slot silindi.')
        return redirect('yonetim_bos_toplu_sil')
    else:
        sayi = qs.count()

    context = {'start': start, 'end': end, 'sayi': sayi, 'silinen': silinen}
    return render(request, 'randevu/yonetim_bos_toplu_sil.html', context)


# --- YENİ: Raporlar (Admin) ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def yonetim_raporlar(request):
    """
    Tarih aralığına göre:
      - Günlük toplam ve durum bazlı sayı
      - Temsilciye göre dağılım (yalnızca dolu randevular)
      - Firmaya göre dağılım (temsilci profili üzerinden)
    Basit grafikler Chart.js ile gösterilir.
    """
    start = request.GET.get('start')
    end = request.GET.get('end')

    base = Randevu.objects.all()
    if start:
        base = base.filter(tarih_saat__date__gte=start)
    if end:
        base = base.filter(tarih_saat__date__lte=end)

    # Günlük özet
    gunluk = (
        base
        .annotate(day=TruncDate('tarih_saat'))
        .values('day')
        .annotate(
            total=Count('id'),
            beklemede=Count('id', filter=Q(status='beklemede')),
            onaylandi=Count('id', filter=Q(status='onaylandi')),
            tamamlandi=Count('id', filter=Q(status='tamamlandi')),
            gelinmedi=Count('id', filter=Q(status='gelinmedi')),
        )
        .order_by('day')
    )

    # Temsilciye göre (dolu randevular)
    per_temsilci = (
        base.filter(temsilci__isnull=False)
        .values('temsilci__first_name', 'temsilci__last_name', 'temsilci__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:20]
    )

    # Firmaya göre (temsilcinin profili > firma)
    per_firma = (
        base.filter(temsilci__temsilciprofili__firma__isnull=False)
        .values('temsilci__temsilciprofili__firma__ad')
        .annotate(total=Count('id'))
        .order_by('-total')[:20]
    )

    # Chart.js için veri listeleri
    labels = [g['day'].strftime('%Y-%m-%d') for g in gunluk]
    totals = [g['total'] for g in gunluk]
    bek = [g['beklemede'] for g in gunluk]
    onay = [g['onaylandi'] for g in gunluk]
    tam = [g['tamamlandi'] for g in gunluk]
    gel = [g['gelinmedi'] for g in gunluk]

    context = {
        'start': start or '',
        'end': end or '',
        'gunluk': gunluk,
        'per_temsilci': per_temsilci,
        'per_firma': per_firma,
        'labels': labels,
        'totals': totals,
        'bek': bek,
        'onay': onay,
        'tam': tam,
        'gel': gel,
    }
    return render(request, 'randevu/yonetim_raporlar.html', context)
