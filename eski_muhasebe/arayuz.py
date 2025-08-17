# arayuz.py (Tüm Düzeltmeleri ve Fatura İndirme Özelliğini İçeren Final Sürüm)

import ttkbootstrap as tb
from tkinter import simpledialog, Listbox, END, VERTICAL, X, Y, BOTH, LEFT, RIGHT, TOP
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from datetime import date, timedelta
from functools import partial
import base64
import tempfile
import os
import webbrowser
import ayarlar_yonetimi
import veritabani_yonetimi
import efatura_servis
import xml.etree.ElementTree as ET

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dateutil.relativedelta import relativedelta

# === 1. PROGRAM BAŞLANGIÇ VE AYARLAR ===
veritabani_yonetimi.ilk_kurulum()
ayarlar = ayarlar_yonetimi.ayarlari_yukle()
gider_kategorileri_listesi = ayarlar.get("gider_kategorileri", [])
satis_tipleri_listesi = ayarlar.get("satis_tipleri", [])
gelen_faturalar_cache = []
giden_faturalar_cache = []

tema_adi = ayarlar.get("tema", "litera")
pencere = tb.Window(themename=tema_adi)
pencere.title("Rüya Eczanesi - Yönetim Paneli")
pencere.geometry("1400x850")
style = pencere.style

# === 3. TÜM FONKSİYONLARIN TANIMLANMASI ===

def ciz_finansal_durum_grafigi(parent_frame, toplam_gelir, toplam_gider):
    for widget in parent_frame.winfo_children():
        widget.destroy()
    if toplam_gelir == 0 and toplam_gider == 0:
        tb.Label(parent_frame, text="Grafik için veri bulunamadı.").pack(pady=20)
        return
    labels = ['Toplam Gelir', 'Toplam Gider']
    values = [toplam_gelir, toplam_gider]
    colors = [style.colors.success, style.colors.danger]
    fig = Figure(figsize=(5, 3.5), dpi=100, facecolor=style.colors.bg)
    ax = fig.add_subplot(111)
    bars = ax.bar(labels, values, color=colors)
    ax.set_title('Gelir - Gider Kıyaslaması', color=style.colors.fg)
    ax.set_ylabel('Tutar (TL)', color=style.colors.fg)
    ax.tick_params(colors=style.colors.fg)
    ax.spines['top'].set_visible(False);
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(style.colors.fg);
    ax.spines['left'].set_color(style.colors.fg)
    ax.set_facecolor(style.colors.inputbg)
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, yval, f'{yval:,.2f} TL', va='bottom', ha='center',
                color=style.colors.fg)
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


def finansal_durum_raporla():
    bas_tarih = fd_bas_tarih_entry.get_date()
    bit_tarih = fd_bit_tarih_entry.get_date()
    if bas_tarih > bit_tarih:
        Messagebox.show_error("Hata", "Başlangıç tarihi, bitiş tarihinden sonra olamaz.")
        return
    bas_tarih_str = bas_tarih.strftime('%Y-%m-%d')
    bit_tarih_str = bit_tarih.strftime('%Y-%m-%d')

    veri = veritabani_yonetimi.finansal_ozet_getir(bas_tarih_str, bit_tarih_str)

    for i in fd_gelir_tree.get_children(): fd_gelir_tree.delete(i)
    for i in fd_gider_tree.get_children(): fd_gider_tree.delete(i)

    toplam_gelir = 0
    if veri['gelirler']:
        for gelir in sorted(veri['gelirler'], key=lambda x: x['tarih']):
            tutar = gelir['tutar'] if gelir['tutar'] is not None else 0
            toplam_gelir += tutar
            fd_gelir_tree.insert("", END, values=(gelir['tarih'], gelir['tip'], gelir['aciklama'], f"{tutar:,.2f} TL"))

    toplam_gider = 0
    if veri['giderler']:
        for gider in sorted(veri['giderler'], key=lambda x: x['tarih']):
            tutar = gider['tutar'] if gider['tutar'] is not None else 0
            toplam_gider += tutar
            fd_gider_tree.insert("", END, values=(gider['tarih'], gider['tip'], gider['aciklama'], f"{tutar:,.2f} TL"))

    net_bakiye = toplam_gelir - toplam_gider
    gelir_var.set(f"{toplam_gelir:,.2f} TL")
    gider_var.set(f"{toplam_gider:,.2f} TL")
    bakiye_var.set(f"{net_bakiye:,.2f} TL")
    bakiye_deger_label.configure(bootstyle="success" if net_bakiye >= 0 else "danger")
    ciz_finansal_durum_grafigi(fd_grafik_cercevesi, toplam_gelir, toplam_gider)


def kredi_ekleme_penceresi_ac():
    kredi_pencere = tb.Toplevel(title="Yeni Banka Kredisi Girişi");
    kredi_pencere.geometry("500x350");
    kredi_pencere.grab_set()
    frame = tb.Frame(kredi_pencere, padding="20");
    frame.pack(fill='both', expand=True)
    tb.Label(frame, text="Banka Adı:").grid(row=0, column=0, sticky='w', pady=4)
    banka_entry = tb.Entry(frame, width=40);
    banka_entry.grid(row=0, column=1, pady=4)
    tb.Label(frame, text="Kredi Açıklaması:").grid(row=1, column=0, sticky='w', pady=4)
    aciklama_entry = tb.Entry(frame, width=40);
    aciklama_entry.grid(row=1, column=1, pady=4)
    tb.Label(frame, text="Kredi Çekim Tarihi:").grid(row=2, column=0, sticky='w', pady=4)
    tarih_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=2, column=1, pady=4)
    tb.Label(frame, text="Aylık Taksit Tutarı (TL):").grid(row=3, column=0, sticky='w', pady=4)
    taksit_tutar_entry = tb.Entry(frame, width=40);
    taksit_tutar_entry.grid(row=3, column=1, pady=4)
    tb.Label(frame, text="Taksit Sayısı (Ay):").grid(row=4, column=0, sticky='w', pady=4)
    taksit_sayi_entry = tb.Entry(frame, width=40);
    taksit_sayi_entry.grid(row=4, column=1, pady=4)

    def kaydet_logigi():
        try:
            banka, tutar, sayi = banka_entry.get(), float(taksit_tutar_entry.get()), int(taksit_sayi_entry.get())
            if not banka or tutar <= 0 or sayi <= 0:
                Messagebox.show_error("Hata",
                                      "Banka adı, taksit tutarı ve taksit sayısı alanları doğru doldurulmalıdır.",
                                      parent=kredi_pencere);
                return
            if veritabani_yonetimi.kredi_ekle(banka, aciklama_entry.get(), tarih_entry.get_date(), sayi, tutar):
                Messagebox.show_info("Başarılı", "Kredi ve taksitleri başarıyla oluşturuldu.", parent=kredi_pencere)
                kredi_tablosunu_yenile();
                kredi_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir veritabanı hatası oluştu.", parent=kredi_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar ve sayı alanları geçerli rakamlar olmalıdır.", parent=kredi_pencere)

    kaydet_btn = tb.Button(frame, text="Krediyi Kaydet ve Taksitlendir", command=kaydet_logigi, bootstyle="primary")
    kaydet_btn.grid(row=5, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def kredi_tablosunu_yenile():
    for i in kredi_tree.get_children(): kredi_tree.delete(i)
    bugun = date.today()
    for taksit in veritabani_yonetimi.kredi_taksitlerini_getir():
        tags, onay_kutusu_degeri = (), ""
        vade_tarihi = date.fromisoformat(taksit['vade_tarihi'])
        if taksit['durum'] == 'Ödendi':
            tags = ('odendi',)
        else:
            onay_kutusu_degeri = "☐"
            if vade_tarihi < bugun: tags = ('odenmedi',)
        kredi_tree.insert("", END, iid=taksit['taksit_id'], tags=tags, values=(
        onay_kutusu_degeri, taksit['vade_tarihi'], taksit['banka_adi'], taksit['kredi_aciklamasi'],
        f"{taksit['taksit_tutari']:.2f} TL", taksit['durum']))


def on_kredi_taksit_click(event):
    region, column = kredi_tree.identify("region", event.x, event.y), kredi_tree.identify_column(event.x)
    if region == "cell" and column == "#1":
        secili_iid = kredi_tree.identify_row(event.y)
        if not secili_iid: return
        if kredi_tree.item(secili_iid, "values")[0] == "☐":
            if Messagebox.yesno("Onay", "Bu taksiti 'Ödendi' olarak işaretlemek istiyor musunuz?", parent=pencere):
                if veritabani_yonetimi.kredi_taksit_durum_guncelle(int(secili_iid), "Ödendi"):
                    kredi_tablosunu_yenile()
                else:
                    Messagebox.show_error("Hata", "Durum güncellenirken bir sorun oluştu.")


def kredi_sil_logigi():
    secili_iid = kredi_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce tablodan bir taksit seçin."); return
    taksit_listesi = veritabani_yonetimi.kredi_taksitlerini_getir()
    secili_taksit_item = next((item for item in taksit_listesi if item['taksit_id'] == int(secili_iid)), None)
    if not secili_taksit_item: Messagebox.show_error("Hata", "Kredi bilgisi bulunamadı."); return
    kredi_id, banka_adi, aciklama = secili_taksit_item['kredi_id'], secili_taksit_item['banka_adi'], secili_taksit_item[
        'kredi_aciklamasi']
    if Messagebox.yesno("Onay",
                        f"'{banka_adi} - {aciklama}' kredisini ve BÜTÜN taksitlerini kalıcı olarak silmek istediğinizden emin misiniz?",
                        parent=pencere):
        if veritabani_yonetimi.kredi_sil(kredi_id):
            Messagebox.show_info("Başarılı", "Kredi ve bağlı taksitleri silindi."); kredi_tablosunu_yenile()
        else:
            Messagebox.show_error("Hata", "Kredi silinirken bir hata oluştu.")


def z_raporu_penceresi_ac():
    z_pencere = tb.Toplevel(title="Günlük Z Raporu Girişi");
    z_pencere.geometry("500x350");
    z_pencere.grab_set()
    frame = tb.Frame(z_pencere, padding="20");
    frame.pack(fill='both', expand=True)
    tb.Label(frame, text="Rapor Tarihi:").grid(row=0, column=0, sticky='w', pady=4)
    tarih_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=0, column=1, pady=4)
    tb.Separator(frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=10)
    tb.Label(frame, text="Genel Toplam (KDV Dahil):").grid(row=2, column=0, sticky='w', pady=4)
    genel_toplam_entry = tb.Entry(frame, width=40);
    genel_toplam_entry.grid(row=2, column=1, pady=4)
    tb.Label(frame, text="Toplam KDV Tutarı (%1):").grid(row=3, column=0, sticky='w', pady=4)
    kdv1_entry = tb.Entry(frame, width=40);
    kdv1_entry.grid(row=3, column=1, pady=4)
    tb.Label(frame, text="Toplam KDV Tutarı (%10):").grid(row=4, column=0, sticky='w', pady=4)
    kdv10_entry = tb.Entry(frame, width=40);
    kdv10_entry.grid(row=4, column=1, pady=4)
    tb.Label(frame, text="Toplam KDV Tutarı (%20):").grid(row=5, column=0, sticky='w', pady=4)
    kdv20_entry = tb.Entry(frame, width=40);
    kdv20_entry.grid(row=5, column=1, pady=4)

    def kaydet_logigi():
        try:
            tarih, genel_toplam = tarih_entry.get_date().strftime('%Y-%m-%d'), float(genel_toplam_entry.get() or 0)
            kdv1, kdv10, kdv20 = float(kdv1_entry.get() or 0), float(kdv10_entry.get() or 0), float(
                kdv20_entry.get() or 0)
            if genel_toplam <= 0: Messagebox.show_error("Hata", "Genel Toplam alanı zorunludur.",
                                                        parent=z_pencere); return
            if veritabani_yonetimi.z_raporu_ekle(tarih, genel_toplam, kdv1, kdv10, kdv20):
                Messagebox.show_info("Başarılı", "Z Raporu başarıyla kaydedildi/güncellendi.", parent=z_pencere)
                z_raporu_tablosunu_yenile();
                z_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir veritabanı hatası oluştu.", parent=z_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar alanları sayısal ve geçerli olmalıdır.", parent=z_pencere)

    kaydet_btn = tb.Button(frame, text="Kaydet", command=kaydet_logigi, bootstyle="primary")
    kaydet_btn.grid(row=6, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def z_raporu_tablosunu_yenile():
    for i in z_raporu_tree.get_children(): z_raporu_tree.delete(i)
    for rapor in veritabani_yonetimi.z_raporu_listesi_getir():
        z_raporu_tree.insert("", END, iid=rapor['id'], values=(
        rapor['tarih'], f"{rapor['toplam_tutar']:.2f} TL", f"{rapor['kdv1']:.2f} TL", f"{rapor['kdv10']:.2f} TL",
        f"{rapor['kdv20']:.2f} TL", f"{rapor['kdv_toplam']:.2f} TL"))


def z_raporu_sil_logigi():
    secili_iid = z_raporu_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir Z Raporu seçin."); return
    if Messagebox.yesno("Onay", "Seçili Z Raporu'nu kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.z_raporu_sil(secili_iid):
            z_raporu_tablosunu_yenile()
        else:
            Messagebox.show_error("Hata", "Rapor silinirken bir hata oluştu.")


def kasa_modulu_penceresi_ac():
    kasa_pencere = tb.Toplevel(title="Günlük Kasa Modülü");
    kasa_pencere.geometry("800x700");
    kasa_pencere.grab_set()
    ust_cerceve = tb.Frame(kasa_pencere);
    ust_cerceve.pack(fill='both', expand=True, padx=10, pady=10)
    giris_frame = tb.LabelFrame(ust_cerceve, text="Yeni Kasa Girişi", padding=15);
    giris_frame.pack(fill='x', pady=(0, 10))
    tb.Label(giris_frame, text="Tarih:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
    tarih_entry = tb.DateEntry(giris_frame, width=20, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=0, column=1, padx=5, pady=5)
    tb.Label(giris_frame, text="Nakit Tutar (TL):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
    nakit_entry = tb.Entry(giris_frame, width=23);
    nakit_entry.grid(row=1, column=1, padx=5, pady=5)
    tb.Label(giris_frame, text="Kredi Kartı Tutarı (TL):").grid(row=0, column=2, padx=(20, 5), pady=5, sticky='w')
    kart_entry = tb.Entry(giris_frame, width=23);
    kart_entry.grid(row=0, column=3, padx=5, pady=5)
    gunluk_frame = tb.LabelFrame(ust_cerceve, text="Günlük İşlemler", padding=15);
    gunluk_frame.pack(fill='both', expand=True)
    gunluk_tree = tb.Treeview(gunluk_frame, columns=('tarih', 'nakit', 'kart', 'toplam'), show='headings');
    gunluk_tree.pack(side='left', fill='both', expand=True)
    gunluk_scrollbar = tb.Scrollbar(gunluk_frame, orient=VERTICAL, command=gunluk_tree.yview);
    gunluk_tree.configure(yscroll=gunluk_scrollbar.set);
    gunluk_scrollbar.pack(side=RIGHT, fill=Y)
    gunluk_tree.heading('tarih', text='Tarih');
    gunluk_tree.column('tarih', width=120, anchor='center');
    gunluk_tree.heading('nakit', text='Nakit Tutar');
    gunluk_tree.column('nakit', width=150, anchor='e');
    gunluk_tree.heading('kart', text='Kredi Kartı Tutarı');
    gunluk_tree.column('kart', width=150, anchor='e');
    gunluk_tree.heading('toplam', text='Günlük Toplam');
    gunluk_tree.column('toplam', width=150, anchor='e')
    aylik_frame = tb.LabelFrame(ust_cerceve, text="Aylık Özet Raporu", padding=15);
    aylik_frame.pack(fill='x', pady=(10, 0))
    aylik_tree = tb.Treeview(aylik_frame, columns=('ay', 'nakit', 'kart', 'toplam'), show='headings', height=5);
    aylik_tree.pack(side='left', fill='x', expand=True)
    aylik_scrollbar = tb.Scrollbar(aylik_frame, orient=VERTICAL, command=aylik_tree.yview);
    aylik_tree.configure(yscroll=aylik_scrollbar.set);
    aylik_scrollbar.pack(side=RIGHT, fill=Y)
    aylik_tree.heading('ay', text='Dönem (Ay)');
    aylik_tree.column('ay', anchor='center');
    aylik_tree.heading('nakit', text='Toplam Nakit');
    aylik_tree.column('nakit', anchor='e');
    aylik_tree.heading('kart', text='Toplam Kredi Kartı');
    aylik_tree.column('kart', anchor='e');
    aylik_tree.heading('toplam', text='Aylık Toplam');
    aylik_tree.column('toplam', anchor='e')

    def gunluk_tabloyu_yenile():
        for i in gunluk_tree.get_children(): gunluk_tree.delete(i)
        for satir in veritabani_yonetimi.gunluk_kasa_listesi_getir():
            gunluk_tree.insert("", END, iid=satir['tarih'], values=(
            satir['tarih'], f"{satir['nakit_tutar']:.2f} TL", f"{satir['kart_tutar']:.2f} TL",
            f"{satir['toplam_tutar']:.2f} TL"))

    def aylik_ozeti_yenile():
        for i in aylik_tree.get_children(): aylik_tree.delete(i)
        for satir in veritabani_yonetimi.aylik_kasa_raporu_getir():
            aylik_tree.insert("", END, values=(
            satir['ay'], f"{satir['toplam_nakit']:.2f} TL", f"{satir['toplam_kart']:.2f} TL",
            f"{satir['genel_toplam']:.2f} TL"))

    def tum_kasa_verilerini_yenile():
        gunluk_tabloyu_yenile(); aylik_ozeti_yenile()

    def kaydet_logigi_kasa():
        try:
            tarih, nakit, kart = tarih_entry.get_date().strftime('%Y-%m-%d'), float(nakit_entry.get() or 0), float(
                kart_entry.get() or 0)
            if veritabani_yonetimi.gunluk_kasa_kaydet(tarih, nakit, kart):
                Messagebox.show_info("Başarılı",
                                     f"{tarih_entry.get_date().strftime('%d.%m.%Y')} tarihli kasa verisi kaydedildi/güncellendi.",
                                     parent=kasa_pencere)
                nakit_entry.delete(0, 'end');
                kart_entry.delete(0, 'end');
                tum_kasa_verilerini_yenile()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir veritabanı hatası oluştu.", parent=kasa_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Lütfen tutar alanlarına geçerli sayılar girin.", parent=kasa_pencere)

    def gunluk_kasa_sil_logigi():
        secili_tarih = gunluk_tree.focus()
        if not secili_tarih: Messagebox.show_warning("Uyarı", "Lütfen silmek için tablodan bir kayıt seçin.",
                                                     parent=kasa_pencere); return
        if Messagebox.yesno("Onay",
                            f"{secili_tarih} tarihli kasa kaydını kalıcı olarak silmek istediğinizden emin misiniz?",
                            parent=kasa_pencere):
            if veritabani_yonetimi.gunluk_kasa_sil(secili_tarih):
                Messagebox.show_info("Başarılı", "Kayıt silindi.", parent=kasa_pencere);
                tum_kasa_verilerini_yenile()
            else:
                Messagebox.show_error("Hata", "Kayıt silinirken bir hata oluştu.", parent=kasa_pencere)

    kaydet_btn = tb.Button(giris_frame, text="Kaydet", command=kaydet_logigi_kasa, bootstyle="primary");
    kaydet_btn.grid(row=1, column=3, padx=5, pady=5, ipady=10, sticky='ns')
    sil_btn = tb.Button(gunluk_frame, text="Seçili Kaydı Sil", command=gunluk_kasa_sil_logigi, bootstyle="danger");
    sil_btn.pack(side='bottom', pady=(10, 0), fill='x', ipady=4)
    tum_kasa_verilerini_yenile()


def tarih_araligi_hesapla(secim):
    today = date.today()
    if secim == "Bu Ay":
        bas_tarih = today.replace(day=1); bit_tarih = (bas_tarih + relativedelta(months=1)) - timedelta(days=1)
    elif secim == "Geçen Ay":
        bit_tarih = today.replace(day=1) - timedelta(days=1); bas_tarih = bit_tarih.replace(day=1)
    elif secim == "Bu Yıl":
        bas_tarih = today.replace(month=1, day=1); bit_tarih = today.replace(month=12, day=31)
    else:
        bas_tarih, bit_tarih = None, None
    return bas_tarih, bit_tarih


def yenile_tum_tablolar():
    toplu_alis_tablosunu_yenile();
    kurumsal_satis_tablosunu_yenile(satis_filtre_cb.get());
    gider_tablosunu_yenile()
    z_raporu_tablosunu_yenile();
    kredi_tablosunu_yenile();
    cek_senet_tablosunu_yenile(filtre_cb.get());
    kk_harcama_tablosunu_yenile(kk_filtre_cb.get())


def ciz_gider_grafigi(parent_frame, gider_verisi):
    for widget in parent_frame.winfo_children(): widget.destroy()
    if not gider_verisi:
        tb.Label(parent_frame, text="Bu dönem için gider verisi bulunamadı.").pack(pady=20);
        return
    labels = [row['kategori'] for row in gider_verisi];
    sizes = [row['toplam'] for row in gider_verisi]
    fig = Figure(figsize=(5.5, 5), dpi=100, facecolor=style.colors.bg);
    ax = fig.add_subplot(111)
    wedges, texts, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=140,
                                      textprops=dict(color='white' if 'dark' in style.theme.name else 'black'))
    ax.axis('equal');
    ax.set_title("Giderlerin Kategori Dağılımı", color=style.colors.fg)
    legend = ax.legend(wedges, labels, title="Kategoriler", loc="center left", bbox_to_anchor=(1.1, 0.5))
    legend.get_frame().set_facecolor(style.colors.inputbg)
    for text in legend.get_texts(): text.set_color(style.colors.fg)
    legend.get_title().set_color(style.colors.fg)
    fig.tight_layout(pad=2)
    canvas = FigureCanvasTkAgg(fig, master=parent_frame);
    canvas.draw();
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


def ciz_satis_grafigi(parent_frame, satis_verisi):
    for widget in parent_frame.winfo_children(): widget.destroy()
    if not satis_verisi:
        tb.Label(parent_frame, text="Bu dönem için satış verisi bulunamadı.").pack(pady=20);
        return
    labels = [row['satis_tipi'] for row in satis_verisi];
    values = [row['toplam'] for row in satis_verisi]
    fig = Figure(figsize=(5.5, 5), dpi=100, facecolor=style.colors.bg);
    ax = fig.add_subplot(111)
    bars = ax.bar(labels, values, color=style.colors.primary)
    ax.set_title('Satışların Tipine Göre Dağılımı', color=style.colors.fg);
    ax.set_ylabel('Toplam Tutar (TL)', color=style.colors.fg)
    ax.tick_params(axis='x', labelrotation=45, colors=style.colors.fg);
    ax.tick_params(axis='y', colors=style.colors.fg)
    ax.spines['top'].set_visible(False);
    ax.spines['right'].set_visible(False);
    ax.spines['bottom'].set_color(style.colors.fg);
    ax.spines['left'].set_color(style.colors.fg)
    ax.set_facecolor(style.colors.inputbg);
    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=parent_frame);
    canvas.draw();
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


def paneli_yenile():
    secim = grafik_filtre_cb.get()
    bas_tarih, bit_tarih = tarih_araligi_hesapla(secim)

    if bas_tarih and bit_tarih:
        bas_tarih_str = bas_tarih.strftime('%Y-%m-%d')
        bit_tarih_str = bit_tarih.strftime('%Y-%m-%d')
        gider_verisi = veritabani_yonetimi.kategoriye_gore_gider_getir(bas_tarih_str, bit_tarih_str)
        satis_verisi = veritabani_yonetimi.tipe_gore_satis_getir(bas_tarih_str, bit_tarih_str)
    else:
        gider_verisi = veritabani_yonetimi.kategoriye_gore_gider_getir()
        satis_verisi = veritabani_yonetimi.tipe_gore_satis_getir()

    if satis_verisi is None:
        satis_verisi = []

    toplam_nakit = 0
    toplam_kart = 0
    tum_kasa_gelirleri = veritabani_yonetimi.gunluk_kasa_listesi_getir()
    for kasa_geliri in tum_kasa_gelirleri:
        gelir_tarihi = date.fromisoformat(kasa_geliri['tarih'])
        if (bas_tarih is None and bit_tarih is None) or (bas_tarih <= gelir_tarihi <= bit_tarih):
            toplam_nakit += kasa_geliri['nakit_tutar']
            toplam_kart += kasa_geliri['kart_tutar']

    if toplam_nakit > 0:
        satis_verisi.append({'satis_tipi': 'Kasa Nakit', 'toplam': toplam_nakit})
    if toplam_kart > 0:
        satis_verisi.append({'satis_tipi': 'Kasa Kredi Kartı', 'toplam': toplam_kart})

    ciz_gider_grafigi(gider_grafik_cercevesi, gider_verisi)
    ciz_satis_grafigi(satis_grafik_cercevesi, satis_verisi)


def toplu_alis_tablosunu_yenile():
    for i in alis_tree.get_children(): alis_tree.delete(i)
    for alis in veritabani_yonetimi.toplu_alis_listesi_getir(): alis_tree.insert("", END, iid=alis['fatura_id'],
                                                                                 values=(
                                                                                 alis['tarih'], alis['fatura_no'],
                                                                                 alis['unvan'],
                                                                                 f"{alis['kdv_toplam']:.2f} TL",
                                                                                 f"{alis['genel_toplam']:.2f} TL"))


def kurumsal_satis_tablosunu_yenile(filtre="Tümü"):
    for i in satis_tree.get_children(): satis_tree.delete(i)
    for satis in veritabani_yonetimi.kurumsal_satis_listesi_getir(filtre): satis_tree.insert("", END, iid=satis['id'],
                                                                                             values=(satis['tarih'],
                                                                                                     satis[
                                                                                                         'satis_tipi'],
                                                                                                     f"{satis['genel_toplam']:.2f} TL",
                                                                                                     satis['aciklama']))


def gider_tablosunu_yenile():
    for i in gider_tree.get_children(): gider_tree.delete(i)
    for gider in veritabani_yonetimi.gider_listesi_getir(): gider_tree.insert("", END, iid=gider['gider_id'], values=(
    gider['tarih'], gider['kategori'], gider['aciklama'], f"{gider['toplam_tutar']:.2f} TL"))


def cek_senet_tablosunu_yenile(filtre="Tümü"):
    for i in cek_senet_tree.get_children(): cek_senet_tree.delete(i)
    cek_senet_listesi = veritabani_yonetimi.cek_senet_listesi_getir(filtre);
    bugun = date.today()
    for kayit in cek_senet_listesi:
        tags, onay_kutusu_degeri = (), ""
        vade_tarihi = date.fromisoformat(kayit['vade_tarihi'])
        if kayit['durum'] in ['Tahsil Edildi', 'Ödendi', 'Ciro Edildi']:
            tags = ('odendi',)
        elif kayit['durum'] == 'Karşılıksız':
            tags = ('odenmedi',)
        elif kayit['durum'] == 'Portföyde':
            onay_kutusu_degeri = "☐"
            if vade_tarihi < bugun: tags = ('odenmedi',)
        cek_senet_tree.insert("", END, iid=kayit['id'], tags=tags, values=(
        onay_kutusu_degeri, kayit['vade_tarihi'], kayit['tip'], kayit['kesideci_lehtar'], f"{kayit['tutar']:.2f} TL",
        kayit['durum'], kayit['banka'], kayit['cek_no']))


def kk_harcama_tablosunu_yenile(filtre="Tümü"):
    for i in kk_tree.get_children(): kk_tree.delete(i)
    harcama_listesi = veritabani_yonetimi.kredi_karti_harcamalari_getir(filtre);
    bugun = date.today()
    for harcama in harcama_listesi:
        tags, onay_kutusu_degeri = (), ""
        son_odeme = date.fromisoformat(harcama['son_odeme_tarihi'])
        if harcama['odeme_durumu'] == 'Tamamen Ödendi':
            tags = ('odendi',)
        elif harcama['odeme_durumu'] in ['Ödenecek', 'Kısmi Ödendi']:
            onay_kutusu_degeri = "☐"
            if son_odeme < bugun: tags = ('odenmedi',)
        kk_tree.insert("", END, iid=harcama['id'], tags=tags, values=(
        onay_kutusu_degeri, harcama['son_odeme_tarihi'], harcama['kart_adi'], f"{harcama['tutar']:.2f} TL",
        f"{harcama['kalan_borc']:.2f} TL", harcama['harcama_aciklamasi'], harcama['islem_tarihi'],
        harcama['odeme_durumu']))


def on_cek_senet_click(event):
    region, column = cek_senet_tree.identify("region", event.x, event.y), cek_senet_tree.identify_column(event.x)
    if region == "cell" and column == "#1":
        secili_iid = cek_senet_tree.identify_row(event.y)
        if not secili_iid: return
        if cek_senet_tree.item(secili_iid, "values")[0] == "☐":
            kayit_tipi, yeni_durum, soru = cek_senet_tree.item(secili_iid, "values")[2], "", ""
            if "Alınan" in kayit_tipi:
                yeni_durum, soru = "Tahsil Edildi", "Bu kaydı 'Tahsil Edildi' olarak işaretlemek istiyor musunuz?"
            elif "Verilen" in kayit_tipi:
                yeni_durum, soru = "Ödendi", "Bu kaydı 'Ödendi' olarak işaretlemek istiyor musunuz?"
            if yeni_durum and Messagebox.yesno("Onay", soru, parent=pencere):
                if veritabani_yonetimi.cek_senet_durum_guncelle(secili_iid, yeni_durum):
                    cek_senet_tablosunu_yenile(filtre_cb.get())
                else:
                    Messagebox.show_error("Hata", "Durum güncellenirken bir sorun oluştu.")


def on_kk_click(event):
    region, column = kk_tree.identify("region", event.x, event.y), kk_tree.identify_column(event.x)
    if region == "cell" and column == "#1":
        secili_iid = kk_tree.identify_row(event.y)
        if not secili_iid: return
        if kk_tree.item(secili_iid, "values")[0] == "☐": odeme_penceresi_ac(secili_iid)


def toplu_alis_penceresi_ac():
    alis_pencere = tb.Toplevel(title="Toplu Depo Alışı Girişi");
    alis_pencere.geometry("500x350");
    alis_pencere.grab_set();
    frame = tb.Frame(alis_pencere, padding="20");
    frame.pack(fill='both', expand=True);
    tb.Label(frame, text="Fatura Numarası:").grid(row=0, column=0, sticky='w', pady=4);
    fatura_no_entry = tb.Entry(frame, width=40);
    fatura_no_entry.grid(row=0, column=1, pady=4);
    tb.Label(frame, text="Depo Ünvanı:").grid(row=1, column=0, sticky='w', pady=4);
    cari_unvan_entry = tb.Entry(frame, width=40);
    cari_unvan_entry.grid(row=1, column=1, pady=4);
    tb.Label(frame, text="Fatura Tarihi:").grid(row=2, column=0, sticky='w', pady=4);
    tarih_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=2, column=1, pady=4);
    tb.Separator(frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10);
    tb.Label(frame, text="Fatura Genel Toplamı:").grid(row=4, column=0, sticky='w', pady=4);
    genel_toplam_entry = tb.Entry(frame, width=40);
    genel_toplam_entry.grid(row=4, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%1):").grid(row=5, column=0, sticky='w', pady=4);
    kdv1_entry = tb.Entry(frame, width=40);
    kdv1_entry.grid(row=5, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%10):").grid(row=6, column=0, sticky='w', pady=4);
    kdv10_entry = tb.Entry(frame, width=40);
    kdv10_entry.grid(row=6, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%20):").grid(row=7, column=0, sticky='w', pady=4);
    kdv20_entry = tb.Entry(frame, width=40);
    kdv20_entry.grid(row=7, column=1, pady=4)

    def kaydet_logigi():
        try:
            fatura_no, cari, tarih = fatura_no_entry.get(), cari_unvan_entry.get(), tarih_entry.get_date().strftime(
                '%Y-%m-%d')
            if not fatura_no or not cari: Messagebox.show_error("Hata", "Fatura No ve Depo Ünvanı zorunludur.",
                                                                parent=alis_pencere); return
            genel_toplam = float(genel_toplam_entry.get() or 0);
            kdv1 = float(kdv1_entry.get() or 0);
            kdv10 = float(kdv10_entry.get() or 0);
            kdv20 = float(kdv20_entry.get() or 0)
            if veritabani_yonetimi.toplu_alis_ekle(fatura_no, cari, tarih, genel_toplam, kdv1, kdv10, kdv20):
                Messagebox.show_info("Başarılı", "Depo alışı başarıyla kaydedildi.",
                                     parent=alis_pencere); toplu_alis_tablosunu_yenile(); alis_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir sorun oluştu.", parent=alis_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar alanları sayısal olmalıdır.", parent=alis_pencere)

    kaydet_btn = tb.Button(frame, text="Kaydet", command=kaydet_logigi, bootstyle="primary");
    kaydet_btn.grid(row=8, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def kurumsal_satis_penceresi_ac():
    satis_pencere = tb.Toplevel(title="Kurumsal Satış Girişi");
    satis_pencere.geometry("500x380");
    satis_pencere.grab_set();
    frame = tb.Frame(satis_pencere, padding="20");
    frame.pack(fill='both', expand=True);
    tb.Label(frame, text="Satış Tipi:").grid(row=0, column=0, sticky='w', pady=4);
    satis_tipi_cb = tb.Combobox(frame, values=satis_tipleri_listesi, state='readonly', width=38);
    satis_tipi_cb.grid(row=0, column=1, pady=4);
    satis_tipi_cb.set(satis_tipleri_listesi[0] if satis_tipleri_listesi else "");
    tb.Label(frame, text="Tarih:").grid(row=1, column=0, sticky='w', pady=4);
    tarih_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=1, column=1, pady=4);
    tb.Label(frame, text="Açıklama:").grid(row=2, column=0, sticky='w', pady=4);
    aciklama_entry = tb.Entry(frame, width=40);
    aciklama_entry.grid(row=2, column=1, pady=4);
    tb.Separator(frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10);
    tb.Label(frame, text="Genel Toplam (KDV Dahil):").grid(row=4, column=0, sticky='w', pady=4);
    genel_toplam_entry = tb.Entry(frame, width=40);
    genel_toplam_entry.grid(row=4, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%1):").grid(row=5, column=0, sticky='w', pady=4);
    kdv1_entry = tb.Entry(frame, width=40);
    kdv1_entry.grid(row=5, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%10):").grid(row=6, column=0, sticky='w', pady=4);
    kdv10_entry = tb.Entry(frame, width=40);
    kdv10_entry.grid(row=6, column=1, pady=4)
    tb.Label(frame, text="KDV Tutarı (%20):").grid(row=7, column=0, sticky='w', pady=4);
    kdv20_entry = tb.Entry(frame, width=40);
    kdv20_entry.grid(row=7, column=1, pady=4)

    def kaydet_logigi():
        try:
            tarih = tarih_entry.get_date().strftime('%Y-%m-%d');
            satis_tipi = satis_tipi_cb.get();
            aciklama = aciklama_entry.get()
            genel_toplam = float(genel_toplam_entry.get() or 0);
            kdv1 = float(kdv1_entry.get() or 0);
            kdv10 = float(kdv10_entry.get() or 0);
            kdv20 = float(kdv20_entry.get() or 0)
            if genel_toplam <= 0: Messagebox.show_warning("Uyarı", "Genel Toplam alanı girilmelidir.",
                                                          parent=satis_pencere); return
            if veritabani_yonetimi.kurumsal_satis_ekle(tarih, satis_tipi, genel_toplam, kdv1, kdv10, kdv20, aciklama):
                Messagebox.show_info("Başarılı", "Satış başarıyla kaydedildi.",
                                     parent=satis_pencere); kurumsal_satis_tablosunu_yenile(); satis_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir sorun oluştu.", parent=satis_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar alanları sayısal olmalıdır.", parent=satis_pencere)

    kaydet_btn = tb.Button(frame, text="Kaydet", command=kaydet_logigi, bootstyle="primary");
    kaydet_btn.grid(row=8, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def gider_ekleme_penceresi_ac():
    gider_pencere = tb.Toplevel(title="Yeni Gider Girişi");
    gider_pencere.geometry("450x350");
    gider_pencere.grab_set()
    frame = tb.Frame(gider_pencere, padding="20");
    frame.pack(fill='both', expand=True)

    tb.Label(frame, text="Tarih:").grid(row=0, column=0, sticky='w', pady=5)
    tarih_entry = tb.DateEntry(frame, width=30, dateformat='%Y-%m-%d');
    tarih_entry.grid(row=0, column=1, pady=5)

    tb.Label(frame, text="Gider Kategorisi:").grid(row=1, column=0, sticky='w', pady=5)
    kategori_combobox = tb.Combobox(frame, values=gider_kategorileri_listesi, width=30, state="readonly");
    kategori_combobox.grid(row=1, column=1, pady=5)
    kategori_combobox.set("Kategori Seçin")

    tb.Label(frame, text="Açıklama:").grid(row=2, column=0, sticky='w', pady=5)
    aciklama_entry = tb.Entry(frame, width=32);
    aciklama_entry.grid(row=2, column=1, pady=5)

    tb.Label(frame, text="Ara Toplam (KDV Hariç):").grid(row=3, column=0, sticky='w', pady=5)
    ara_toplam_entry = tb.Entry(frame, width=32);
    ara_toplam_entry.grid(row=3, column=1, pady=5)

    tb.Label(frame, text="KDV Tutarı:").grid(row=4, column=0, sticky='w', pady=5)
    kdv_entry = tb.Entry(frame, width=32);
    kdv_entry.grid(row=4, column=1, pady=5)

    def kaydet_logigi():
        tarih = tarih_entry.get_date().strftime('%Y-%m-%d')
        kategori, aciklama, ara_toplam_str, kdv_str = kategori_combobox.get(), aciklama_entry.get(), ara_toplam_entry.get(), kdv_entry.get()
        if not kategori or not ara_toplam_str or kategori == "Kategori Seçin":
            Messagebox.show_error("Hata", "Kategori ve Ara Toplam alanları zorunludur.", parent=gider_pencere);
            return
        try:
            ara_toplam, kdv_tutari = float(ara_toplam_str), float(kdv_str) if kdv_str else 0.0
            if veritabani_yonetimi.gider_ekle(tarih, kategori, aciklama, ara_toplam, kdv_tutari):
                Messagebox.show_info("Başarılı", "Gider başarıyla kaydedildi.", parent=gider_pencere)
                gider_tablosunu_yenile();
                gider_pencere.destroy()
            else:
                Messagebox.show_error("Veritabanı Hatası", "Gider kaydedilirken bir hata oluştu.", parent=gider_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar alanları sayısal bir değer olmalıdır.", parent=gider_pencere)

    kaydet_btn = tb.Button(frame, text="Gideri Kaydet", command=kaydet_logigi, bootstyle="primary");
    kaydet_btn.grid(row=5, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def gideri_sil_logigi():
    secili_iid = gider_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir gider seçin."); return
    if Messagebox.yesno("Onay", "Seçili gideri kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.gider_sil(secili_iid):
            gider_tablosunu_yenile()
        else:
            Messagebox.show_error("Hata", "Gider silinirken bir hata oluştu.")


def cek_senet_sil_logigi():
    secili_iid = cek_senet_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir kayıt seçin."); return
    if Messagebox.yesno("Onay", "Seçili kaydı kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.cek_senet_sil(secili_iid):
            cek_senet_tablosunu_yenile(filtre_cb.get())
        else:
            Messagebox.show_error("Hata", "Kayıt silinirken bir hata oluştu.")


def kk_harcamasi_sil_logigi():
    secili_iid = kk_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir harcama seçin."); return
    if Messagebox.yesno("Onay", "Seçili harcamayı kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.kredi_karti_harcamasi_sil(secili_iid):
            kk_harcama_tablosunu_yenile(kk_filtre_cb.get())
        else:
            Messagebox.show_error("Hata", "Harcama silinirken bir hata oluştu.")


def kurumsal_satis_sil_logigi():
    secili_iid = satis_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir satış seçin."); return
    if Messagebox.yesno("Onay", "Seçili satışı kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.kurumsal_satis_sil(secili_iid):
            kurumsal_satis_tablosunu_yenile(satis_filtre_cb.get())
        else:
            Messagebox.show_error("Hata", "Satış silinirken bir hata oluştu.")


def toplu_alis_sil_logigi():
    secili_iid = alis_tree.focus()
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir alış faturası seçin."); return
    if Messagebox.yesno("Onay", "Seçili alış faturasını kalıcı olarak silmek istediğinizden emin misiniz?"):
        if veritabani_yonetimi.toplu_alis_sil(secili_iid):
            toplu_alis_tablosunu_yenile()
        else:
            Messagebox.show_error("Hata", "Alış faturası silinirken bir hata oluştu.")


def kdv_raporu_penceresi_ac():
    rapor_pencere = tb.Toplevel(title="Detaylı KDV Raporu");
    rapor_pencere.geometry("500x400");
    rapor_pencere.grab_set()

    def raporu_olustur_logigi():
        bas_tarih_obj, bit_tarih_obj = bas_tarih_entry.get_date(), bit_tarih_entry.get_date()
        if bas_tarih_obj > bit_tarih_obj: Messagebox.show_error("Hata",
                                                                "Başlangıç tarihi, bitiş tarihinden sonra olamaz.",
                                                                parent=rapor_pencere); return
        bas_tarih_str, bit_tarih_str = bas_tarih_obj.strftime('%Y-%m-%d'), bit_tarih_obj.strftime('%Y-%m-%d')
        rapor = veritabani_yonetimi.kdv_raporu_getir(bas_tarih_str, bit_tarih_str)
        hesaplanan_kdv, kdv_alis, kdv_gider = rapor['hesaplanan_kdv'], rapor['indirilecek_kdv_alis'], rapor[
            'indirilecek_kdv_gider']
        toplam_indirilecek = kdv_alis + kdv_gider
        net_kdv = hesaplanan_kdv - toplam_indirilecek
        sonuc_baslik_label.config(
            text=f"{bas_tarih_entry.get_date().strftime('%d.%m.%Y')} - {bit_tarih_entry.get_date().strftime('%d.%m.%Y')} Arası KDV Durumu");
        hesaplanan_kdv_label.config(text=f"(+) Hesaplanan KDV (Satışlar): {hesaplanan_kdv:.2f} TL");
        indirilecek_alis_label.config(text=f"(-) İndirilecek KDV (Mal Alış): {kdv_alis:.2f} TL");
        indirilecek_gider_label.config(text=f"(-) İndirilecek KDV (Giderler): {kdv_gider:.2f} TL");
        net_kdv_label.config(text=f"{net_kdv:.2f} TL");
        net_kdv_aciklama.config(text="ÖDENECEK KDV" if net_kdv >= 0 else "DEVREDEN KDV");
        net_kdv_label.configure(bootstyle="danger" if net_kdv >= 0 else "success")

    frame = tb.Frame(rapor_pencere, padding="10");
    frame.pack(fill='both', expand=True);
    secim_frame = tb.Frame(frame);
    secim_frame.pack(pady=10, fill='x');
    tb.Label(secim_frame, text="Başlangıç:").pack(side='left', padx=5);
    bas_tarih_entry = tb.DateEntry(secim_frame, width=12, dateformat='%Y-%m-%d');
    bas_tarih_entry.pack(side='left');
    tb.Label(secim_frame, text="Bitiş:").pack(side='left', padx=10);
    bit_tarih_entry = tb.DateEntry(secim_frame, width=12, dateformat='%Y-%m-%d');
    bit_tarih_entry.pack(side='left');
    hesapla_btn = tb.Button(secim_frame, text="Raporla", command=raporu_olustur_logigi, bootstyle="primary");
    hesapla_btn.pack(side='left', padx=10);
    sonuc_frame = tb.LabelFrame(frame, text="Sonuç", padding=20);
    sonuc_frame.pack(fill='both', expand=True);
    sonuc_baslik_label = tb.Label(sonuc_frame, text="", font=("Helvetica", 12, "bold"));
    sonuc_baslik_label.pack(pady=5);
    hesaplanan_kdv_label = tb.Label(sonuc_frame, text="", font=("Helvetica", 10));
    hesaplanan_kdv_label.pack(anchor='w', pady=2);
    indirilecek_alis_label = tb.Label(sonuc_frame, text="", font=("Helvetica", 10));
    indirilecek_alis_label.pack(anchor='w', pady=2);
    indirilecek_gider_label = tb.Label(sonuc_frame, text="", font=("Helvetica", 10));
    indirilecek_gider_label.pack(anchor='w', pady=2);
    tb.Separator(sonuc_frame, orient='horizontal').pack(fill='x', pady=10);
    net_kdv_aciklama = tb.Label(sonuc_frame, text="", font=("Helvetica", 12, "bold"));
    net_kdv_aciklama.pack();
    net_kdv_label = tb.Label(sonuc_frame, text="", font=("Helvetica", 20, "bold"));
    net_kdv_label.pack()


def ayarlar_penceresi_ac():
    ayarlar_pencere = tb.Toplevel(title="Ayarlar")
    ayarlar_pencere.geometry("600x550")
    ayarlar_pencere.grab_set()
    notebook = tb.Notebook(ayarlar_pencere)
    notebook.pack(pady=10, padx=10, fill="both", expand=True)

    def create_list_manager(parent, title, item_list_key):
        item_list = ayarlar.get(item_list_key, [])
        frame = tb.Frame(parent, padding=10)
        parent.add(frame, text=title)
        listbox = Listbox(frame, bg=style.colors.inputbg, fg=style.colors.fg, selectbackground=style.colors.primary,
                          selectforeground='white', borderwidth=0, highlightthickness=0)
        for item in item_list: listbox.insert(END, item)
        listbox.pack(pady=5, fill='both', expand=True)

        def add_item():
            yeni_item = simpledialog.askstring(f"Yeni {title[:-1]}", f"Eklemek istediğiniz başlığı girin:",
                                               parent=ayarlar_pencere)
            if yeni_item and yeni_item not in listbox.get(0, END): listbox.insert(END, yeni_item)

        def delete_item():
            if listbox.curselection():
                listbox.delete(listbox.curselection())

        btn_frame = tb.Frame(frame)
        btn_frame.pack(pady=5)
        tb.Button(btn_frame, text="Ekle", command=add_item, bootstyle="success").pack(side='left', padx=5)
        tb.Button(btn_frame, text="Sil", command=delete_item, bootstyle="danger").pack(side='left', padx=5)
        return listbox

    gider_listbox = create_list_manager(notebook, 'Gider Kategorileri', "gider_kategorileri")
    satis_listbox = create_list_manager(notebook, 'Satış Tipleri', "satis_tipleri")

    tema_frame = tb.Frame(notebook, padding=10)
    notebook.add(tema_frame, text='Görünüm')
    tb.Label(tema_frame, text="Uygulama Teması:", font="-weight bold").pack(pady=(10, 5))
    mevcut_temalar = style.theme_names()
    tema_cb = tb.Combobox(tema_frame, values=mevcut_temalar, state='readonly')
    tema_cb.pack(pady=5, padx=10, fill='x')
    mevcut_tema = ayarlar.get("tema", "litera")
    tema_cb.set(mevcut_tema if mevcut_tema in mevcut_temalar else "litera")
    tb.Label(tema_frame,
             text="Tema değişikliğinin etkili olması için\nuygulamanın yeniden başlatılması gerekir.",
             justify="center",
             bootstyle="info").pack(pady=(20, 5), fill='x')

    efatura_ayarlar_frame = tb.Frame(notebook, padding=10)
    notebook.add(efatura_ayarlar_frame, text='e-Fatura Ayarları')
    tb.Label(efatura_ayarlar_frame, text="E-Fatura Entegratör Bilgileri", font="-weight bold").pack(pady=(5, 15))
    k_adi_frame = tb.Frame(efatura_ayarlar_frame)
    k_adi_frame.pack(fill='x', padx=10, pady=5)
    tb.Label(k_adi_frame, text="Kullanıcı Adı:", width=15, anchor='w').pack(side='left')
    efatura_k_adi_entry = tb.Entry(k_adi_frame)
    efatura_k_adi_entry.pack(side='left', fill='x', expand=True)
    efatura_k_adi_entry.insert(0, ayarlar.get("efatura_kullanici_adi", ""))
    sifre_frame = tb.Frame(efatura_ayarlar_frame)
    sifre_frame.pack(fill='x', padx=10, pady=5)
    tb.Label(sifre_frame, text="Şifre:", width=15, anchor='w').pack(side='left')
    efatura_sifre_entry = tb.Entry(sifre_frame, show="*")
    efatura_sifre_entry.pack(side='left', fill='x', expand=True)
    efatura_sifre_entry.insert(0, ayarlar.get("efatura_sifre", ""))
    tb.Label(efatura_ayarlar_frame,
             text="Bu bilgileri kaydettikten sonra programı yeniden başlatmanız\ngerekebilir.",
             justify="center", bootstyle="info").pack(pady=(20, 5), fill='x')

    def ayarlari_kaydet_ve_kapat():
        global gider_kategorileri_listesi, satis_tipleri_listesi
        gider_kategorileri_listesi = list(gider_listbox.get(0, END))
        ayarlar["gider_kategorileri"] = gider_kategorileri_listesi
        satis_tipleri_listesi = list(satis_listbox.get(0, END))
        ayarlar["satis_tipleri"] = satis_tipleri_listesi
        ayarlar["tema"] = tema_cb.get()
        ayarlar["efatura_kullanici_adi"] = efatura_k_adi_entry.get()
        ayarlar["efatura_sifre"] = efatura_sifre_entry.get()
        ayarlar_yonetimi.ayarlari_kaydet(ayarlar)
        Messagebox.show_info("Ayarlar Kaydedildi",
                             "Değişiklikler kaydedildi. Lütfen programı yeniden başlatın.",
                             parent=ayarlar_pencere)
        ayarlar_pencere.destroy()

    kaydet_btn = tb.Button(ayarlar_pencere, text="Ayarları Kaydet ve Kapat", command=ayarlari_kaydet_ve_kapat,
                           bootstyle="primary")
    kaydet_btn.pack(pady=10, padx=10, fill='x', ipady=5)


def cek_senet_penceresi_ac():
    cs_pencere = tb.Toplevel(title="Yeni Çek/Senet Girişi");
    cs_pencere.geometry("500x450");
    cs_pencere.grab_set();
    frame = tb.Frame(cs_pencere, padding="20");
    frame.pack(fill='both', expand=True);
    tb.Label(frame, text="Tip:").grid(row=0, column=0, sticky='w', pady=2);
    tip_cb = tb.Combobox(frame, values=["Alınan Çek", "Verilen Çek", "Alınan Senet", "Verilen Senet"], state='readonly',
                         width=38);
    tip_cb.grid(row=0, column=1, pady=2);
    tip_cb.set("Alınan Çek");
    tb.Label(frame, text="Düzenleme Tarihi:").grid(row=1, column=0, sticky='w', pady=2);
    duzenleme_tarihi_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    duzenleme_tarihi_entry.grid(row=1, column=1, pady=2);
    tb.Label(frame, text="Vade Tarihi:").grid(row=2, column=0, sticky='w', pady=2);
    vade_tarihi_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    vade_tarihi_entry.grid(row=2, column=1, pady=2);
    tb.Label(frame, text="Keşideci / Lehtar:").grid(row=3, column=0, sticky='w', pady=2);
    taraf_entry = tb.Entry(frame, width=40);
    taraf_entry.grid(row=3, column=1, pady=2);
    tb.Label(frame, text="Tutar (TL):").grid(row=4, column=0, sticky='w', pady=2);
    tutar_entry = tb.Entry(frame, width=40);
    tutar_entry.grid(row=4, column=1, pady=2);
    tb.Label(frame, text="Banka:").grid(row=5, column=0, sticky='w', pady=2);
    banka_entry = tb.Entry(frame, width=40);
    banka_entry.grid(row=5, column=1, pady=2);
    tb.Label(frame, text="Çek Numarası:").grid(row=6, column=0, sticky='w', pady=2);
    cek_no_entry = tb.Entry(frame, width=40);
    cek_no_entry.grid(row=6, column=1, pady=2);
    tb.Label(frame, text="Açıklama:").grid(row=7, column=0, sticky='w', pady=2);
    aciklama_entry = tb.Entry(frame, width=40);
    aciklama_entry.grid(row=7, column=1, pady=2)

    def kaydet_logigi():
        try:
            if not tutar_entry.get() or not taraf_entry.get(): Messagebox.show_error("Hata",
                                                                                     "Tip, Taraf ve Tutar alanları zorunludur.",
                                                                                     parent=cs_pencere); return
            if veritabani_yonetimi.cek_senet_ekle(tip_cb.get(), vade_tarihi_entry.get_date().strftime('%Y-%m-%d'),
                                                  duzenleme_tarihi_entry.get_date().strftime('%Y-%m-%d'),
                                                  float(tutar_entry.get()), taraf_entry.get(), banka_entry.get(),
                                                  cek_no_entry.get(), "Portföyde", aciklama_entry.get()):
                Messagebox.show_info("Başarılı", "Kayıt başarıyla eklendi.", parent=cs_pencere);
                cek_senet_tablosunu_yenile();
                cs_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt eklenirken bir sorun oluştu.", parent=cs_pencere)
        except (ValueError, TypeError):
            Messagebox.show_error("Hata", "Tutar ve Tarih alanları doğru formatta olmalıdır.", parent=cs_pencere)

    kaydet_btn = tb.Button(frame, text="Kaydet", command=kaydet_logigi, bootstyle="primary");
    kaydet_btn.grid(row=8, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def durum_guncelle_penceresi_ac():
    secili_iid = cek_senet_tree.focus();
    if not secili_iid: Messagebox.show_warning("Uyarı", "Lütfen önce listeden bir kayıt seçin."); return
    yeni_durum = simpledialog.askstring("Durum Güncelle",
                                        "Yeni durumu girin (Örn: Tahsil Edildi, Ödendi, Ciro Edildi, Karşılıksız):",
                                        parent=pencere)
    if yeni_durum and yeni_durum.strip() != "":
        if veritabani_yonetimi.cek_senet_durum_guncelle(secili_iid, yeni_durum.strip()):
            Messagebox.show_info("Başarılı", "Durum güncellendi."); cek_senet_tablosunu_yenile(filtre_cb.get())
        else:
            Messagebox.show_error("Hata", "Durum güncellenirken bir sorun oluştu.")


def kredi_karti_penceresi_ac():
    kk_pencere = tb.Toplevel(title="Yeni Kredi Kartı Harcaması");
    kk_pencere.geometry("500x350");
    kk_pencere.grab_set();
    frame = tb.Frame(kk_pencere, padding="20");
    frame.pack(fill='both', expand=True);
    tb.Label(frame, text="Kart Adı:").grid(row=0, column=0, sticky='w', pady=4);
    kart_adi_entry = tb.Entry(frame, width=40);
    kart_adi_entry.grid(row=0, column=1, pady=4);
    tb.Label(frame, text="Harcama Açıklaması:").grid(row=1, column=0, sticky='w', pady=4);
    aciklama_entry = tb.Entry(frame, width=40);
    aciklama_entry.grid(row=1, column=1, pady=4);
    tb.Label(frame, text="Tutar (TL):").grid(row=2, column=0, sticky='w', pady=4);
    tutar_entry = tb.Entry(frame, width=40);
    tutar_entry.grid(row=2, column=1, pady=4);
    tb.Label(frame, text="İşlem Tarihi:").grid(row=3, column=0, sticky='w', pady=4);
    islem_tarihi_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    islem_tarihi_entry.grid(row=3, column=1, pady=4);
    tb.Label(frame, text="Ekstre Son Ödeme Tarihi:").grid(row=4, column=0, sticky='w', pady=4);
    son_odeme_entry = tb.DateEntry(frame, width=38, dateformat='%Y-%m-%d');
    son_odeme_entry.grid(row=4, column=1, pady=4)

    def kaydet_logigi():
        try:
            kart_adi, aciklama = kart_adi_entry.get(), aciklama_entry.get()
            tutar = float(tutar_entry.get() or 0)
            islem_tarihi = islem_tarihi_entry.get_date().strftime('%Y-%m-%d');
            son_odeme_tarihi = son_odeme_entry.get_date().strftime('%Y-%m-%d')
            if not kart_adi or tutar <= 0: Messagebox.show_error("Hata", "Kart Adı ve Tutar alanları zorunludur.",
                                                                 parent=kk_pencere); return
            if veritabani_yonetimi.kredi_karti_harcamasi_ekle(kart_adi, aciklama, tutar, islem_tarihi,
                                                              son_odeme_tarihi):
                Messagebox.show_info("Başarılı", "Kredi kartı harcaması başarıyla kaydedildi.",
                                     parent=kk_pencere); kk_harcama_tablosunu_yenile(); kk_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir sorun oluştu.", parent=kk_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Tutar alanı sayısal olmalıdır.", parent=kk_pencere)

    kaydet_btn = tb.Button(frame, text="Kaydet", command=kaydet_logigi, bootstyle="primary");
    kaydet_btn.grid(row=5, column=0, columnspan=2, pady=20, ipady=10, sticky='ew')


def odeme_penceresi_ac(harcama_id):
    odeme_pencere = tb.Toplevel(title="Kredi Kartı Ödemesi Yap");
    odeme_pencere.geometry("400x250");
    odeme_pencere.grab_set()
    frame = tb.Frame(odeme_pencere, padding="20");
    frame.pack(fill='both', expand=True)
    mevcut_borc_str = kk_tree.item(harcama_id, "values")[4]
    mevcut_borc = float(mevcut_borc_str.replace(" TL", "").replace(",", ""))
    tb.Label(frame, text=f"Kalan Borç: {mevcut_borc:.2f} TL", font=("Helvetica", 12, "bold")).pack(pady=10)
    tb.Label(frame, text="Ödeme Tutarı:").pack(pady=5);
    odeme_entry = tb.Entry(frame, width=20);
    odeme_entry.pack(pady=5)

    def odemeyi_kaydet():
        try:
            odenen_tutar = float(odeme_entry.get())
            if odenen_tutar <= 0: Messagebox.show_warning("Uyarı", "Ödeme tutarı sıfırdan büyük olmalıdır.",
                                                          parent=odeme_pencere); return
            if odenen_tutar > mevcut_borc: Messagebox.show_warning("Uyarı",
                                                                   f"Ödeme tutarı kalan borçtan ({mevcut_borc:.2f} TL) fazla olamaz.",
                                                                   parent=odeme_pencere); return
            if veritabani_yonetimi.kk_odeme_yap(harcama_id, odenen_tutar):
                Messagebox.show_info("Başarılı", "Ödeme kaydedildi.", parent=odeme_pencere)
                kk_harcama_tablosunu_yenile(kk_filtre_cb.get());
                odeme_pencere.destroy()
            else:
                Messagebox.show_error("Hata", "Ödeme kaydedilirken bir sorun oluştu.", parent=odeme_pencere)
        except ValueError:
            Messagebox.show_error("Hata", "Lütfen geçerli bir sayısal tutar girin.", parent=odeme_pencere)

    kaydet_btn = tb.Button(frame, text="Ödemeyi Kaydet", command=odemeyi_kaydet, bootstyle="primary");
    kaydet_btn.pack(pady=20, ipady=8, fill='x')


def gelen_faturalari_sorgula_ve_goster(bas_tarih, bit_tarih):
    global gelen_faturalar_cache

    if bas_tarih > bit_tarih:
        Messagebox.show_error("Hata", "Başlangıç tarihi, bitiş tarihinden sonra olamaz.")
        return

    for i in efatura_tree.get_children():
        efatura_tree.delete(i)
    gelen_faturalar_cache.clear()

    aktarilmis_alis_uuidler = veritabani_yonetimi.get_all_imported_fatura_uuids()
    aktarilmis_gider_uuidler = veritabani_yonetimi.get_all_imported_gider_uuids()
    tum_aktarilmis_uuidler = aktarilmis_alis_uuidler.union(aktarilmis_gider_uuidler)

    sonuc = efatura_servis.get_inbox_documents(bas_tarih, bit_tarih)

    if isinstance(sonuc, str):
        Messagebox.show_error("Hata", sonuc)
        return

    if not sonuc or not hasattr(sonuc, 'documentsCount') or sonuc['documentsCount'] == 0:
        aciklama = getattr(sonuc, 'stateExplanation', "Belirtilen tarih aralığında gelen kutunuzda yeni fatura bulunamadı.")
        Messagebox.show_info("Bilgi", aciklama)
        return

    fatura_listesi = sonuc['documents']
    
    Messagebox.show_info("Bilgi", f"Gelen kutusunda {len(fatura_listesi)} adet fatura bulundu. Liste güncelleniyor.")

    try:
        for fatura_item in fatura_listesi:
            uuid = getattr(fatura_item, 'document_uuid', 'UUID_YOK')
            fatura_no = getattr(fatura_item, 'document_id', 'NO_YOK')
            tarih = getattr(fatura_item, 'document_issue_date', 'TARİH_YOK')
            gonderen = getattr(fatura_item, 'source_title', 'GÖNDEREN_YOK')
            xml_icerik = getattr(fatura_item, 'xmlContent', None)

            kdv_dahil_tutar_val = getattr(fatura_item, 'taxInclusiveAmount', None)
            kdv_haric_tutar_val = getattr(fatura_item, 'taxExlusiveAmount', None)

            kdv_dahil_tutar = float(kdv_dahil_tutar_val) if kdv_dahil_tutar_val is not None else 0.0
            kdv_haric_tutar = float(kdv_haric_tutar_val) if kdv_haric_tutar_val is not None else 0.0

            kdv_toplam = kdv_dahil_tutar - kdv_haric_tutar

            fatura_detay = {
               "uuid": uuid, "fatura_no": fatura_no, "tarih": str(tarih),
               "gonderen": gonderen, "tutar": kdv_dahil_tutar, "kdv_tutar": kdv_toplam,
               "xml_content": xml_icerik # XML içeriğini önbelleğe ekle
            }

            gelen_faturalar_cache.append(fatura_detay)

            tag = ()
            durum_text = "Sorgulandı"
            if uuid in tum_aktarilmis_uuidler:
                tag = ('islenmis',)
                durum_text = "İçe Aktarıldı"

            efatura_tree.insert("", END, iid=fatura_detay['uuid'], tags=tag, values=(
                "☐", # Onay kutusu
                fatura_detay['tarih'], fatura_detay['gonderen'],
                fatura_detay['fatura_no'], f"{fatura_detay['tutar']:.2f} TL", durum_text
            ))
    except Exception as e:
        Messagebox.show_error("Veri Ayrıştırma Hatası", f"Faturalar listeye eklenirken bir hata oluştu: {e}")
        import traceback
        print(f"AYRIŞTIRMA HATASI: {traceback.format_exc()}")

def giden_faturalari_sorgula_ve_goster(bas_tarih, bit_tarih):
    global giden_faturalar_cache
    if bas_tarih > bit_tarih:
        Messagebox.show_error("Hata", "Başlangıç tarihi, bitiş tarihinden sonra olamaz.")
        return

    for i in giden_efatura_tree.get_children():
        giden_efatura_tree.delete(i)
    giden_faturalar_cache.clear()

    aktarilmis_satis_uuidler = veritabani_yonetimi.get_all_imported_kurumsal_satis_uuids()

    sonuc = efatura_servis.get_outbox_documents(bas_tarih, bit_tarih)

    if isinstance(sonuc, str):
        Messagebox.show_error("Hata", sonuc)
        return

    if not sonuc or not hasattr(sonuc, 'documentsCount') or sonuc['documentsCount'] == 0:
        Messagebox.show_info("Bilgi", "Belirtilen tarih aralığında giden kutunuzda fatura bulunamadı.")
        return

    fatura_listesi = sonuc['documents']
    Messagebox.show_info("Bilgi", f"Giden kutusunda {len(fatura_listesi)} adet fatura bulundu.")

    for fatura_item in fatura_listesi:
        uuid = getattr(fatura_item, 'document_uuid', 'UUID_YOK')
        fatura_no = getattr(fatura_item, 'document_id', 'NO_YOK')
        tarih = getattr(fatura_item, 'document_issue_date', 'TARİH_YOK')
        alici = getattr(fatura_item, 'destination_title', 'ALICI_YOK')
        durum_text_api = getattr(fatura_item, 'state_explanation', 'DURUM_YOK')
        
        kdv_dahil_tutar_val = getattr(fatura_item, 'taxInclusiveAmount', None)
        kdv_haric_tutar_val = getattr(fatura_item, 'taxExlusiveAmount', None)

        kdv_dahil_tutar = float(kdv_dahil_tutar_val) if kdv_dahil_tutar_val is not None else 0.0
        kdv_haric_tutar = float(kdv_haric_tutar_val) if kdv_haric_tutar_val is not None else 0.0
        kdv_toplam = kdv_dahil_tutar - kdv_haric_tutar

        fatura_detay = {
            "uuid": uuid, "fatura_no": fatura_no, "tarih": str(tarih),
            "alici": alici, "tutar": kdv_dahil_tutar, "kdv_tutar": kdv_toplam
        }
        giden_faturalar_cache.append(fatura_detay)
        
        tag = ()
        durum_text = durum_text_api
        if uuid in aktarilmis_satis_uuidler:
            tag = ('islenmis',)
            durum_text = "İçe Aktarıldı"

        giden_efatura_tree.insert("", END, iid=uuid, tags=tag, values=(
            str(tarih), alici, fatura_no, f"{kdv_dahil_tutar:,.2f} TL", durum_text
        ))

def secili_faturayi_indir_ve_ac():
    """Seçili gelen faturayı işler ve tarayıcıda açar."""
    # Standart seçim yerine, 'checked' olarak etiketlenmiş item'ları bul
    checked_items = []
    for item_id in efatura_tree.get_children():
        if 'checked' in efatura_tree.item(item_id, 'tags'):
            checked_items.append(item_id)

    # Seçim durumunu kontrol et
    if not checked_items:
        Messagebox.show_warning("Uyarı", "Lütfen görüntülemek için tablodan bir faturanın kutucuğunu işaretleyin.")
        return
    if len(checked_items) > 1:
        Messagebox.show_warning("Uyarı", "Lütfen aynı anda sadece bir fatura seçerek görüntüleme yapın.")
        return

    secili_uuid = checked_items[0]

    # Artık 'values' içindeki kolon sırasını doğru veriyoruz (kutucuk ilk sırada olduğu için)
    # 'sec'(0), 'tarih'(1), 'gonderen'(2), 'fatura_no'(3)
    fatura_no = efatura_tree.item(secili_uuid, 'values')[3] 
    fatura_no_safe = "".join(c for c in fatura_no if c.isalnum() or c in ('-', '_')).rstrip()

    pencere.config(cursor="watch")
    pencere.update_idletasks()

    try:
        download_path = os.path.join(tempfile.gettempdir(), 'RüyaEczaneFaturalar', fatura_no_safe)
        os.makedirs(download_path, exist_ok=True)

        basarili, sonuc = efatura_servis.download_and_process_invoice(secili_uuid, download_path, 'inbox')

        if basarili:
            webbrowser.open(f'file:///{os.path.realpath(sonuc)}')
        else:
            Messagebox.show_error("İndirme Başarısız", sonuc)

    except Exception as e:
        Messagebox.show_error("Hata", f"Dosyalar indirilirken/açılırken genel bir hata oluştu: {e}")
    finally:
        pencere.config(cursor="")
def secili_giden_faturayi_goruntule():
    """Seçili giden faturayı işler ve tarayıcıda açar."""
    # Giden faturalar tablosunda henüz checkbox yok, standart seçim kullanılıyor.
    # Eğer ona da checkbox eklersek bu kod bloğu aşağıdaki gibi değiştirilmeli.
    # Şimdilik standart bırakıyoruz, çünkü giden faturalara checkbox eklemedik.
    secili_items = giden_efatura_tree.selection()
    if not secili_items:
        Messagebox.show_warning("Uyarı", "Lütfen önce tablodan bir giden fatura seçin.")
        return

    secili_uuid = secili_items[0]

    fatura_no = giden_efatura_tree.item(secili_uuid, 'values')[2]
    fatura_no_safe = "".join(c for c in fatura_no if c.isalnum() or c in ('-', '_')).rstrip()

    pencere.config(cursor="watch")
    pencere.update_idletasks()

    try:
        download_path = os.path.join(tempfile.gettempdir(), 'RüyaEczaneFaturalar', fatura_no_safe)
        os.makedirs(download_path, exist_ok=True)

        basarili, sonuc = efatura_servis.download_and_process_invoice(secili_uuid, download_path, 'outbox')

        if basarili:
            webbrowser.open(f'file:///{os.path.realpath(sonuc)}')
        else:
            Messagebox.show_error("İndirme Başarısız", sonuc)

    except Exception as e:
        Messagebox.show_error("Hata", f"Dosyalar indirilirken/açılırken genel bir hata oluştu: {e}")
    finally:
        pencere.config(cursor="")
def secili_faturayi_isle_penceresi_ac():
    secili_uuid = efatura_tree.focus()
    if not secili_uuid:
        Messagebox.show_warning("Uyarı", "Lütfen önce tablodan içe aktarılacak bir fatura seçin.")
        return

    if 'islenmis' in efatura_tree.item(secili_uuid, 'tags'):
        Messagebox.show_info("Bilgi", "Bu fatura zaten daha önce içe aktarılmış.")
        return

    secili_fatura = next((f for f in gelen_faturalar_cache if f['uuid'] == secili_uuid), None)
    if not secili_fatura:
        Messagebox.show_error("Hata", "Seçili fatura bilgileri bulunamadı.")
        return

    islem_pencere = tb.Toplevel(title="e-Faturayı İşle");
    islem_pencere.geometry("450x300");
    islem_pencere.grab_set()
    frame = tb.Frame(islem_pencere, padding="15");
    frame.pack(fill='both', expand=True)

    tb.Label(frame, text=f"Firma: {secili_fatura['gonderen']}", font="-weight bold").pack(anchor='w')
    tb.Label(frame, text=f"Tutar: {secili_fatura['tutar']:.2f} TL").pack(anchor='w', pady=(0,10))

    def kaydet_ve_kapat(islem_tipi):
        if islem_tipi == 'alis':
            basarili, mesaj = veritabani_yonetimi.efatura_ice_aktar(
                fatura_uuid=secili_fatura['uuid'], fatura_no=secili_fatura['fatura_no'],
                cari_unvan=secili_fatura['gonderen'], tarih=secili_fatura['tarih'],
                genel_toplam=secili_fatura['tutar'], kdv_toplam=secili_fatura['kdv_tutar']
            )
            if basarili:
                Messagebox.show_info("Başarılı", mesaj, parent=islem_pencere)
                current_values = list(efatura_tree.item(secili_uuid, 'values'))
                current_values[4] = "İçe Aktarıldı"
                efatura_tree.item(secili_uuid, tags=('islenmis',), values=tuple(current_values))
                toplu_alis_tablosunu_yenile()
                islem_pencere.destroy()
            else:
                Messagebox.show_error("İçe Aktarma Başarısız", mesaj, parent=islem_pencere)
        
        elif islem_tipi == 'gider':
            kategori = kategori_cb.get()
            aciklama = aciklama_entry.get()
            if not kategori or kategori == "Kategori Seçin":
                Messagebox.show_warning("Uyarı", "Lütfen bir gider kategorisi seçin.", parent=islem_pencere)
                return
            
            basarili, mesaj = veritabani_yonetimi.efatura_gider_olarak_ice_aktar(
                fatura_uuid=secili_fatura['uuid'], cari_unvan=secili_fatura['gonderen'],
                tarih=secili_fatura['tarih'], genel_toplam=secili_fatura['tutar'],
                kdv_toplam=secili_fatura['kdv_tutar'], kategori=kategori, aciklama=aciklama
            )
            if basarili:
                Messagebox.show_info("Başarılı", mesaj, parent=islem_pencere)
                current_values = list(efatura_tree.item(secili_uuid, 'values'))
                current_values[4] = "İçe Aktarıldı"
                efatura_tree.item(secili_uuid, tags=('islenmis',), values=tuple(current_values))
                gider_tablosunu_yenile()
                islem_pencere.destroy()
            else:
                Messagebox.show_error("İçe Aktarma Başarısız", mesaj, parent=islem_pencere)

    alis_btn = tb.Button(frame, text="Depo Alışı Olarak Kaydet", bootstyle="success", command=lambda: kaydet_ve_kapat('alis'))
    alis_btn.pack(fill='x', ipady=8, pady=5)
    
    tb.Separator(frame).pack(fill='x', pady=10)

    gider_frame = tb.LabelFrame(frame, text="Veya Gider Olarak Kaydet", padding=10)
    gider_frame.pack(fill='x')

    tb.Label(gider_frame, text="Gider Kategorisi:").grid(row=0, column=0, sticky='w', pady=2)
    kategori_cb = tb.Combobox(gider_frame, values=gider_kategorileri_listesi, state="readonly", width=25)
    kategori_cb.grid(row=0, column=1, sticky='w', pady=2)
    kategori_cb.set("Kategori Seçin")
    
    tb.Label(gider_frame, text="Ek Açıklama:").grid(row=1, column=0, sticky='w', pady=2)
    aciklama_entry = tb.Entry(gider_frame, width=27)
    aciklama_entry.grid(row=1, column=1, sticky='w', pady=2)

    gider_btn = tb.Button(gider_frame, text="Gider Olarak Kaydet", bootstyle="danger", command=lambda: kaydet_ve_kapat('gider'))
    gider_btn.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10,0), ipady=5)

def giden_faturayi_ice_aktar_penceresi_ac():
    secili_uuid = giden_efatura_tree.focus()
    if not secili_uuid:
        Messagebox.show_warning("Uyarı", "Lütfen önce tablodan içe aktarılacak bir fatura seçin.")
        return

    if 'islenmis' in giden_efatura_tree.item(secili_uuid, 'tags'):
        Messagebox.show_info("Bilgi", "Bu fatura zaten daha önce içe aktarılmış.")
        return

    secili_fatura = next((f for f in giden_faturalar_cache if f['uuid'] == secili_uuid), None)
    if not secili_fatura:
        Messagebox.show_error("Hata", "Seçili giden fatura bilgileri önbellekte bulunamadı.")
        return

    islem_pencere = tb.Toplevel(title="Giden e-Faturayı Kurumsal Satış Olarak İşle")
    islem_pencere.geometry("450x300")
    islem_pencere.grab_set()
    frame = tb.Frame(islem_pencere, padding="15")
    frame.pack(fill='both', expand=True)

    tb.Label(frame, text=f"Alıcı: {secili_fatura['alici']}", font="-weight bold").pack(anchor='w')
    tb.Label(frame, text=f"Fatura No: {secili_fatura['fatura_no']}").pack(anchor='w')
    tb.Label(frame, text=f"Tutar: {secili_fatura['tutar']:.2f} TL").pack(anchor='w', pady=(0, 15))

    tb.Label(frame, text="Satış Tipi:").pack(anchor='w', pady=(5, 2))
    satis_tipi_cb = tb.Combobox(frame, values=satis_tipleri_listesi, state='readonly')
    satis_tipi_cb.pack(fill='x', pady=(0, 10))
    if satis_tipleri_listesi:
        satis_tipi_cb.set(satis_tipleri_listesi[0])

    tb.Label(frame, text="Ek Açıklama:").pack(anchor='w', pady=(5, 2))
    aciklama_entry = tb.Entry(frame)
    aciklama_entry.pack(fill='x')

    def kaydet_ve_kapat():
        satis_tipi = satis_tipi_cb.get()
        if not satis_tipi:
            Messagebox.show_warning("Uyarı", "Lütfen bir satış tipi seçin.", parent=islem_pencere)
            return

        basarili, mesaj = veritabani_yonetimi.efatura_kurumsal_satis_olarak_ice_aktar(
            fatura_uuid=secili_fatura['uuid'],
            fatura_no=secili_fatura['fatura_no'],
            alici_unvan=secili_fatura['alici'],
            tarih=secili_fatura['tarih'],
            genel_toplam=secili_fatura['tutar'],
            kdv_toplam=secili_fatura['kdv_tutar'],
            satis_tipi=satis_tipi,
            aciklama=aciklama_entry.get()
        )

        if basarili:
            Messagebox.show_info("Başarılı", mesaj, parent=islem_pencere)
            current_values = list(giden_efatura_tree.item(secili_uuid, 'values'))
            current_values[4] = "İçe Aktarıldı"
            giden_efatura_tree.item(secili_uuid, tags=('islenmis',), values=tuple(current_values))
            kurumsal_satis_tablosunu_yenile()
            islem_pencere.destroy()
        else:
            Messagebox.show_error("İçe Aktarma Başarısız", mesaj, parent=islem_pencere)

    kaydet_btn = tb.Button(frame, text="Kurumsal Satış Olarak Kaydet", bootstyle="primary", command=kaydet_ve_kapat)
    kaydet_btn.pack(side='bottom', fill='x', ipady=8, pady=(20, 0))


def secili_faturalari_toplu_alis_olarak_aktar():
    """Treeview'de 'checked' olarak etiketlenmiş faturaları 'Toplu Alış' olarak içeri aktarır."""
    secili_uuids = []
    # Treeview'deki tüm item'ları kontrol et
    for item_id in efatura_tree.get_children():
        # Eğer 'checked' tag'ı varsa listeye ekle
        if 'checked' in efatura_tree.item(item_id, 'tags'):
            secili_uuids.append(item_id)

    if not secili_uuids:
        Messagebox.show_warning("Uyarı", "Toplu aktarım için önce tablodan en az bir faturayı kutucuğu işaretleyerek seçmelisiniz.")
        return

    basarili_sayac = 0
    atlanan_sayac = 0
    hatali_sayac = 0

    for uuid in secili_uuids:
        if 'islenmis' in efatura_tree.item(uuid, 'tags'):
            atlanan_sayac += 1
            continue

        fatura_data = next((f for f in gelen_faturalar_cache if f['uuid'] == uuid), None)
        if not fatura_data:
            hatali_sayac += 1
            print(f"Hata: {uuid} UUID'li fatura önbellekte bulunamadı.")
            continue

        basarili, mesaj = veritabani_yonetimi.efatura_ice_aktar(
            fatura_uuid=fatura_data['uuid'],
            fatura_no=fatura_data['fatura_no'],
            cari_unvan=fatura_data['gonderen'],
            tarih=fatura_data['tarih'],
            genel_toplam=fatura_data['tutar'],
            kdv_toplam=fatura_data['kdv_tutar']
        )

        if basarili:
            basarili_sayac += 1
            current_values = list(efatura_tree.item(uuid, 'values'))
            current_values[4] = "İçe Aktarıldı" # Durum kolonunu güncelle
            # 'checked' tag'ini kaldır ve 'islenmis' olarak bırak
            efatura_tree.item(uuid, tags=('islenmis',), values=tuple(current_values))
        else:
            hatali_sayac += 1
            print(f"İçe aktarma hatası ({uuid}): {mesaj}")

    toplu_alis_tablosunu_yenile()

    sonuc_mesaji = f"Toplu Aktarım Tamamlandı!\n\n" \
                   f"Başarıyla Aktarılan: {basarili_sayac}\n" \
                   f"Daha Önce Aktarıldığı İçin Atlanan: {atlanan_sayac}\n" \
                   f"Hatalı: {hatali_sayac}"
    Messagebox.show_info("İşlem Sonucu", sonuc_mesaji)


def kasa_hesaplama_penceresi_ac():
    kasa_pencere = tb.Toplevel(title="Günlük Kasa Hesaplama Modülü")
    kasa_pencere.geometry("1100x750")
    kasa_pencere.grab_set()

    sol_frame = tb.LabelFrame(kasa_pencere, text="İşlem Formu", padding=15)
    sol_frame.pack(side='left', fill='y', padx=10, pady=10)

    tb.Label(sol_frame, text="İşlem Tarihi:").grid(row=0, column=0, sticky='w', pady=8)
    tarih_entry = tb.DateEntry(sol_frame, width=15, dateformat='%Y-%m-%d')
    tarih_entry.grid(row=0, column=1, pady=8)

    def verileri_doldur(event=None):
        tarih_str = tarih_entry.get_date().strftime('%Y-%m-%d')
        veri = veritabani_yonetimi.kasa_hesabi_getir(tarih_str)
        
        for entry in [baslangic_entry, sistem_nakit_entry, cikis_entry, sayilan_entry, aciklama_entry]:
            is_readonly = entry.cget('state') == 'readonly'
            if is_readonly: entry.config(state='normal')
            entry.delete(0, 'end')
            if is_readonly: entry.config(state='readonly')

        if veri:
            sistem_nakit_entry.config(state='normal')
            sistem_nakit_entry.insert(0, str(veri.get('sistem_nakit_geliri', '0.0')))
            sistem_nakit_entry.config(state='readonly')
            
            baslangic_entry.insert(0, str(veri.get('baslangic_tutari', '0.0')))
            cikis_entry.insert(0, str(veri.get('kasadan_cikis_toplami', '0.0')))
            sayilan_entry.insert(0, str(veri.get('sayilan_nakit', '0.0')))
            aciklama_entry.insert(0, str(veri.get('aciklama', '')))
    
    tarih_entry.bind("<<DateEntrySelected>>", verileri_doldur)

    tb.Label(sol_frame, text="Programdaki Nakit Gelir\n(Günlük Kasa Modülünden):", justify='left').grid(row=1, column=0, sticky='w', pady=8)
    sistem_nakit_entry = tb.Entry(sol_frame, width=18, state="readonly")
    sistem_nakit_entry.grid(row=1, column=1, pady=8)
    
    tb.Label(sol_frame, text="Kasa Başlangıç Tutarı (Devir):").grid(row=2, column=0, sticky='w', pady=8)
    baslangic_entry = tb.Entry(sol_frame, width=18)
    baslangic_entry.grid(row=2, column=1, pady=8)

    tb.Label(sol_frame, text="Kasadan Çıkan Toplam Para:").grid(row=3, column=0, sticky='w', pady=8)
    cikis_entry = tb.Entry(sol_frame, width=18)
    cikis_entry.grid(row=3, column=1, pady=8)
    
    tb.Separator(sol_frame, orient='horizontal').grid(row=4, columnspan=2, sticky='ew', pady=10)
    
    tb.Label(sol_frame, text="Fiili Sayılan Nakit Tutar:", font="-weight bold").grid(row=5, column=0, sticky='w', pady=8)
    sayilan_entry = tb.Entry(sol_frame, width=18, bootstyle="info")
    sayilan_entry.grid(row=5, column=1, pady=8)

    tb.Label(sol_frame, text="Açıklama (Çıkan Para Detayı vb.):").grid(row=6, column=0, sticky='w', pady=8)
    aciklama_entry = tb.Entry(sol_frame, width=18)
    aciklama_entry.grid(row=6, column=1, pady=8)

    sag_frame = tb.LabelFrame(kasa_pencere, text="Geçmiş Kasa Hesapları", padding=15)
    sag_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

    columns = ('tarih', 'baslangic', 'gelir', 'cikis', 'beklenen', 'sayilan', 'fark', 'durum')
    kasa_tree = tb.Treeview(sag_frame, columns=columns, show='headings')
    kasa_tree.pack(fill='both', expand=True)
    
    kasa_tree.heading('tarih', text='Tarih'); kasa_tree.column('tarih', width=80, anchor='center')
    kasa_tree.heading('baslangic', text='Devir'); kasa_tree.column('baslangic', width=80, anchor='e')
    kasa_tree.heading('gelir', text='Nakit Gelir'); kasa_tree.column('gelir', width=90, anchor='e')
    kasa_tree.heading('cikis', text='Çıkış'); kasa_tree.column('cikis', width=80, anchor='e')
    kasa_tree.heading('beklenen', text='Beklenen'); kasa_tree.column('beklenen', width=90, anchor='e')
    kasa_tree.heading('sayilan', text='Sayılan'); kasa_tree.column('sayilan', width=90, anchor='e')
    kasa_tree.heading('fark', text='Fark'); kasa_tree.column('fark', width=80, anchor='e')
    kasa_tree.heading('durum', text='Durum'); kasa_tree.column('durum', width=120, anchor='center')
    
    kasa_tree.tag_configure('fazla', background=style.colors.success)
    kasa_tree.tag_configure('eksik', background=style.colors.danger)

    def tabloyu_yenile():
        for i in kasa_tree.get_children(): kasa_tree.delete(i)
        for kayit in veritabani_yonetimi.kasa_hesaplarini_listele():
            tag = ''
            if kayit['fark'] > 0.01: tag = 'fazla'
            elif kayit['fark'] < -0.01: tag = 'eksik'
            
            kasa_tree.insert("", "end", iid=kayit['hesap_id'], tags=(tag,), values=(
                kayit['tarih'], f"{kayit['baslangic_tutari']:,.2f} TL",
                f"{kayit['sistem_nakit_geliri']:,.2f} TL", f"{kayit['kasadan_cikis_toplami']:,.2f} TL",
                f"{kayit['beklenen_nakit']:,.2f} TL", f"{kayit['sayilan_nakit']:,.2f} TL",
                f"{kayit['fark']:,.2f} TL", kayit['durum']
            ))
            
    def kaydet_ve_hesapla():
        try:
            tarih = tarih_entry.get_date().strftime('%Y-%m-%d')
            baslangic = float(baslangic_entry.get() or 0)
            sistem_nakit_str = sistem_nakit_entry.get()
            sistem_nakit = float(sistem_nakit_str.replace(' TL', '').replace(',', '') if sistem_nakit_str else 0)
            cikis = float(cikis_entry.get() or 0)
            sayilan = float(sayilan_entry.get() or 0)
            aciklama = aciklama_entry.get()

            if sayilan <= 0:
                Messagebox.show_warning("Uyarı", "Lütfen 'Fiili Sayılan Nakit' tutarını giriniz.", parent=kasa_pencere)
                return

            if veritabani_yonetimi.kasa_hesabi_ekle_guncelle(tarih, baslangic, sistem_nakit, cikis, sayilan, aciklama):
                Messagebox.show_info("Başarılı", f"{tarih} tarihli kasa hesabı kaydedildi/güncellendi.", parent=kasa_pencere)
                tabloyu_yenile()
            else:
                Messagebox.show_error("Hata", "Kayıt sırasında bir hata oluştu.", parent=kasa_pencere)
        except ValueError:
            Messagebox.show_error("Geçersiz Değer", "Lütfen tüm tutar alanlarına geçerli sayılar girin.", parent=kasa_pencere)

    def secili_kaydi_sil():
        secili_id = kasa_tree.focus()
        if not secili_id:
            Messagebox.show_warning("Uyarı", "Lütfen silmek için tablodan bir kayıt seçin.", parent=kasa_pencere); return
        if Messagebox.yesno("Onay", "Seçili kasa hesabını kalıcı olarak silmek istiyor musunuz?", parent=kasa_pencere):
            if veritabani_yonetimi.kasa_hesabi_sil(secili_id):
                Messagebox.show_info("Başarılı", "Kayıt silindi.", parent=kasa_pencere); tabloyu_yenile()
            else:
                Messagebox.show_error("Hata", "Silme işlemi sırasında bir hata oluştu.", parent=kasa_pencere)

    def secili_kaydi_duzenle():
        secili_id = kasa_tree.focus()
        if not secili_id:
            Messagebox.show_warning("Uyarı", "Lütfen düzenlemek için tablodan bir kayıt seçin.", parent=kasa_pencere); return
        secili_degerler = kasa_tree.item(secili_id, "values")
        tarih_str = secili_degerler[0]
        tarih_entry.set_date(date.fromisoformat(tarih_str))
        verileri_doldur()

    btn_frame = tb.Frame(sol_frame)
    btn_frame.grid(row=7, columnspan=2, pady=20)
    tb.Button(btn_frame, text="Hesapla ve Kaydet/Güncelle", command=kaydet_ve_hesapla, bootstyle="primary").pack(fill='x', ipady=5, pady=5)
    
    sag_btn_frame = tb.Frame(sag_frame)
    sag_btn_frame.pack(side='bottom', fill='x', pady=(10,0))
    tb.Button(sag_btn_frame, text="Seçili Kaydı Sil", command=secili_kaydi_sil, bootstyle="danger").pack(side='right', padx=5)
    tb.Button(sag_btn_frame, text="Seçili Kaydı Düzenle", command=secili_kaydi_duzenle, bootstyle="secondary").pack(side='right')

    verileri_doldur()
    tabloyu_yenile()

# === 4. WIDGET YERLEŞİMİ VE PROGRAM BAŞLANGICI ===

ust_frame = tb.Frame(pencere)
ust_frame.pack(fill=X, pady=5, padx=10)
tb.Button(ust_frame, text="Toplu Alış", command=toplu_alis_penceresi_ac, bootstyle="success").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Z Raporu", command=z_raporu_penceresi_ac, bootstyle="warning").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Kurumsal Satış", command=kurumsal_satis_penceresi_ac, bootstyle="warning").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Yeni Gider", command=gider_ekleme_penceresi_ac, bootstyle="danger").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Çek/Senet", command=cek_senet_penceresi_ac, bootstyle="info").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Kredi Kartı", command=kredi_karti_penceresi_ac, bootstyle="info").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Banka Kredisi", command=kredi_ekleme_penceresi_ac, bootstyle="primary-outline").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="KDV Raporu", command=kdv_raporu_penceresi_ac, bootstyle="secondary-outline").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Günlük Kasa", command=kasa_modulu_penceresi_ac, bootstyle="success-outline").pack(side=LEFT, padx=3)
tb.Button(ust_frame, text="Kasa Hesapla", command=kasa_hesaplama_penceresi_ac, bootstyle="dark").pack(side=LEFT, padx=3)

tb.Button(ust_frame, text="🔄 Yenile", command=yenile_tum_tablolar, bootstyle="secondary-outline").pack(side=RIGHT, padx=3)
tb.Button(ust_frame, text="⚙️ Ayarlar", command=ayarlar_penceresi_ac, bootstyle="secondary").pack(side=RIGHT, padx=3)

notebook = tb.Notebook(pencere)
notebook.pack(pady=5, padx=10, fill="both", expand=True)

finansal_durum_tab_frame = tb.Frame(notebook, padding=10)
grafik_tab_frame = tb.Frame(notebook, padding=10)
alis_tab_frame = tb.Frame(notebook, padding=10)
satis_tab_frame = tb.Frame(notebook, padding=10)
gider_tab_frame = tb.Frame(notebook, padding=10)
z_raporu_tab_frame = tb.Frame(notebook, padding=10)
kredi_tab_frame = tb.Frame(notebook, padding=10)
cek_senet_tab_frame = tb.Frame(notebook, padding=10)
kk_tab_frame = tb.Frame(notebook, padding=10)
efatura_tab_frame = tb.Frame(notebook, padding=10)

notebook.add(finansal_durum_tab_frame, text='💰 Finansal Durum')
fd_ust_cerceve = tb.Frame(finansal_durum_tab_frame);
fd_ust_cerceve.pack(fill='x', pady=5)
tb.Label(fd_ust_cerceve, text="Başlangıç Tarihi:").pack(side='left', padx=5)
fd_bas_tarih_entry = tb.DateEntry(fd_ust_cerceve, width=12, dateformat='%Y-%m-%d');
fd_bas_tarih_entry.pack(side='left', padx=5)
fd_bas_tarih_entry.set_date(date.today().replace(day=1))
tb.Label(fd_ust_cerceve, text="Bitiş Tarihi:").pack(side='left', padx=5)
fd_bit_tarih_entry = tb.DateEntry(fd_ust_cerceve, width=12, dateformat='%Y-%m-%d');
fd_bit_tarih_entry.pack(side='left', padx=5)
tb.Button(fd_ust_cerceve, text="🔄 Raporla", command=finansal_durum_raporla, bootstyle="primary").pack(side='left', padx=10)
fd_ana_cerceve = tb.Frame(finansal_durum_tab_frame);
fd_ana_cerceve.pack(fill='both', expand=True, pady=10)
fd_sol_cerceve = tb.Frame(fd_ana_cerceve);
fd_sol_cerceve.pack(side='left', fill='both', expand=True, padx=(0, 5))
fd_sag_cerceve = tb.Frame(fd_ana_cerceve);
fd_sag_cerceve.pack(side='right', fill='y', padx=(5, 0))
fd_ozet_cercevesi = tb.LabelFrame(fd_sag_cerceve, text="Özet", padding=10);
fd_ozet_cercevesi.pack(fill='x')
gelir_var = tb.StringVar(value="0.00 TL");
gider_var = tb.StringVar(value="0.00 TL");
bakiye_var = tb.StringVar(value="0.00 TL")
tb.Label(fd_ozet_cercevesi, text="Toplam Gelir:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky='w', pady=4)
tb.Label(fd_ozet_cercevesi, textvariable=gelir_var, bootstyle='success', font=("Helvetica", 10)).grid(row=0, column=1, sticky='e', pady=4, padx=5)
tb.Label(fd_ozet_cercevesi, text="Toplam Gider:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky='w', pady=4)
tb.Label(fd_ozet_cercevesi, textvariable=gider_var, bootstyle='danger', font=("Helvetica", 10)).grid(row=1, column=1, sticky='e', pady=4, padx=5)
tb.Separator(fd_ozet_cercevesi).grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
tb.Label(fd_ozet_cercevesi, text="Net Bakiye:", font=("Helvetica", 12, "bold")).grid(row=3, column=0, sticky='w', pady=6)
bakiye_deger_label = tb.Label(fd_ozet_cercevesi, textvariable=bakiye_var, font=("Helvetica", 12, "bold"));
bakiye_deger_label.grid(row=3, column=1, sticky='e', pady=6, padx=5)
fd_grafik_cercevesi = tb.LabelFrame(fd_sag_cerceve, text="Grafik", padding=10);
fd_grafik_cercevesi.pack(fill='both', expand=True, pady=(10, 0))
fd_detay_cercevesi = tb.Frame(fd_sol_cerceve);
fd_detay_cercevesi.pack(fill='both', expand=True)
fd_gelir_frame = tb.LabelFrame(fd_detay_cercevesi, text="Gelir Kalemleri", padding=5);
fd_gelir_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
fd_gider_frame = tb.LabelFrame(fd_detay_cercevesi, text="Gider Kalemleri", padding=5);
fd_gider_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
fd_gelir_tree = tb.Treeview(fd_gelir_frame, columns=('tarih', 'tip', 'aciklama', 'tutar'), show='headings', height=10)
fd_gider_tree = tb.Treeview(fd_gider_frame, columns=('tarih', 'tip', 'aciklama', 'tutar'), show='headings', height=10)

def setup_treeview_finansal(parent, tree):
    tree.pack(side='left', fill='both', expand=True)
    scrollbar = tb.Scrollbar(parent, orient='vertical', command=tree.yview);
    tree.configure(yscrollcommand=scrollbar.set);
    scrollbar.pack(side='right', fill='y')
    tree.heading('tarih', text='Tarih');
    tree.column('tarih', width=80, anchor='center')
    tree.heading('tip', text='İşlem Tipi');
    tree.column('tip', width=120)
    tree.heading('aciklama', text='Açıklama');
    tree.column('aciklama', width=180)
    tree.heading('tutar', text='Tutar');
    tree.column('tutar', width=100, anchor='e')

setup_treeview_finansal(fd_gelir_frame, fd_gelir_tree)
setup_treeview_finansal(fd_gider_frame, fd_gider_tree)

notebook.add(grafik_tab_frame, text='📊 Gösterge Paneli')
filtre_cercevesi = tb.Frame(grafik_tab_frame);
filtre_cercevesi.pack(fill='x', pady=5, padx=5)
tb.Label(filtre_cercevesi, text="Zaman Aralığı:").pack(side='left', padx=(0, 5))
grafik_filtre_cb = tb.Combobox(filtre_cercevesi, values=["Bu Ay", "Geçen Ay", "Bu Yıl", "Tüm Zamanlar"], state='readonly', width=15)
grafik_filtre_cb.pack(side='left');
grafik_filtre_cb.set("Bu Ay")
tb.Button(filtre_cercevesi, text="🔄 Raporla", command=paneli_yenile, bootstyle="primary").pack(side='left', padx=10)
grafik_ana_cerceve = tb.Frame(grafik_tab_frame);
grafik_ana_cerceve.pack(fill='both', expand=True)
gider_grafik_cercevesi = tb.LabelFrame(grafik_ana_cerceve, text="Gider Dağılımı");
gider_grafik_cercevesi.pack(side='left', fill='both', expand=True, padx=10, pady=5)
satis_grafik_cercevesi = tb.LabelFrame(grafik_ana_cerceve, text="Satış Dağılımı");
satis_grafik_cercevesi.pack(side='left', fill='both', expand=True, padx=10, pady=5)

notebook.add(alis_tab_frame, text='Depo Alışları')
alis_ust_frame = tb.Frame(alis_tab_frame);
alis_ust_frame.pack(fill='x', pady=(0, 5))
tb.Button(alis_ust_frame, text="Seçili Alışı Sil", command=toplu_alis_sil_logigi, bootstyle="danger-outline").pack(side='left')
alis_tree = tb.Treeview(alis_tab_frame, columns=('tarih', 'fatura_no', 'unvan', 'kdv', 'tutar'), show='headings');
alis_tree.pack(side='left', fill='both', expand=True)
alis_scrollbar = tb.Scrollbar(alis_tab_frame, orient=VERTICAL, command=alis_tree.yview);
alis_tree.configure(yscroll=alis_scrollbar.set);
alis_scrollbar.pack(side=RIGHT, fill=Y)
alis_tree.heading('tarih', text='Tarih');
alis_tree.column('tarih', width=120);
alis_tree.heading('fatura_no', text='Fatura No');
alis_tree.column('fatura_no', width=150);
alis_tree.heading('unvan', text='Depo Ünvanı');
alis_tree.column('unvan', width=300);
alis_tree.heading('kdv', text='Toplam KDV');
alis_tree.column('kdv', width=120, anchor='e');
alis_tree.heading('tutar', text='Genel Toplam');
alis_tree.column('tutar', width=150, anchor='e')

notebook.add(satis_tab_frame, text='Kurumsal Satışlar')
satis_ust_frame = tb.Frame(satis_tab_frame);
satis_ust_frame.pack(fill='x', pady=(0, 5))
tb.Label(satis_ust_frame, text="Tipe Göre Filtrele:").pack(side='left', padx=(0, 5))
satis_filtre_cb = tb.Combobox(satis_ust_frame, values=["Tümü"] + satis_tipleri_listesi, state='readonly', width=20);
satis_filtre_cb.pack(side='left');
satis_filtre_cb.set("Tümü")
tb.Button(satis_ust_frame, text="Filtrele", command=lambda: kurumsal_satis_tablosunu_yenile(satis_filtre_cb.get()), bootstyle="info").pack(side='left', padx=5)
tb.Button(satis_ust_frame, text="Seçili Satışı Sil", command=kurumsal_satis_sil_logigi, bootstyle="danger-outline").pack(side='left', padx=5)
satis_tree = tb.Treeview(satis_tab_frame, columns=('tarih', 'tip', 'tutar', 'aciklama'), show='headings');
satis_tree.pack(side='left', fill='both', expand=True)
satis_scrollbar = tb.Scrollbar(satis_tab_frame, orient=VERTICAL, command=satis_tree.yview);
satis_tree.configure(yscroll=satis_scrollbar.set);
satis_scrollbar.pack(side=RIGHT, fill=Y)
satis_tree.heading('tarih', text='Tarih');
satis_tree.column('tarih', width=100);
satis_tree.heading('tip', text='Satış Tipi');
satis_tree.column('tip', width=200);
satis_tree.heading('tutar', text='Genel Toplam');
satis_tree.column('tutar', width=150, anchor='e');
satis_tree.heading('aciklama', text='Açıklama');
satis_tree.column('aciklama', width=400)

notebook.add(gider_tab_frame, text='Giderler')
gider_ust_frame = tb.Frame(gider_tab_frame);
gider_ust_frame.pack(fill='x', pady=(0, 5))
tb.Button(gider_ust_frame, text="Seçili Gideri Sil", command=gideri_sil_logigi, bootstyle="danger-outline").pack(side='left')
gider_tree = tb.Treeview(gider_tab_frame, columns=('tarih', 'kategori', 'aciklama', 'tutar'), show='headings');
gider_tree.pack(side='left', fill='both', expand=True)
gider_scrollbar = tb.Scrollbar(gider_tab_frame, orient=VERTICAL, command=gider_tree.yview);
gider_tree.configure(yscroll=gider_scrollbar.set);
gider_scrollbar.pack(side=RIGHT, fill=Y)
gider_tree.heading('tarih', text='Tarih');
gider_tree.column('tarih', width=100);
gider_tree.heading('kategori', text='Kategori');
gider_tree.column('kategori', width=150);
gider_tree.heading('aciklama', text='Açıklama');
gider_tree.column('aciklama', width=350);
gider_tree.heading('tutar', text='Toplam Tutar');
gider_tree.column('tutar', width=120, anchor='e')

notebook.add(z_raporu_tab_frame, text='Z Raporları')
z_rapor_ust_frame = tb.Frame(z_raporu_tab_frame);
z_rapor_ust_frame.pack(fill='x', pady=(0, 5))
tb.Button(z_rapor_ust_frame, text="Seçili Raporu Sil", command=z_raporu_sil_logigi, bootstyle="danger-outline").pack(side='left')
z_raporu_tree = tb.Treeview(z_raporu_tab_frame, columns=('tarih', 'toplam', 'kdv1', 'kdv10', 'kdv20', 'toplam_kdv'), show='headings');
z_raporu_tree.pack(side='left', fill='both', expand=True)
z_rapor_scrollbar = tb.Scrollbar(z_raporu_tab_frame, orient=VERTICAL, command=z_raporu_tree.yview);
z_raporu_tree.configure(yscroll=z_rapor_scrollbar.set);
z_rapor_scrollbar.pack(side=RIGHT, fill=Y)
z_raporu_tree.heading('tarih', text='Tarih');
z_raporu_tree.column('tarih', width=100, anchor='center');
z_raporu_tree.heading('toplam', text='Toplam Tutar');
z_raporu_tree.column('toplam', width=150, anchor='e');
z_raporu_tree.heading('kdv1', text='KDV %1');
z_raporu_tree.column('kdv1', width=120, anchor='e');
z_raporu_tree.heading('kdv10', text='KDV %10');
z_raporu_tree.column('kdv10', width=120, anchor='e');
z_raporu_tree.heading('kdv20', text='KDV %20');
z_raporu_tree.column('kdv20', width=120, anchor='e');
z_raporu_tree.heading('toplam_kdv', text='Toplam KDV');
z_raporu_tree.column('toplam_kdv', width=120, anchor='e')

notebook.add(kredi_tab_frame, text='Banka Kredileri')
kredi_ust_frame = tb.Frame(kredi_tab_frame);
kredi_ust_frame.pack(fill='x', pady=(0, 5))
tb.Button(kredi_ust_frame, text="Seçili Krediyi Sil", command=kredi_sil_logigi, bootstyle="danger-outline").pack(side='left')
kredi_liste_frame = tb.Frame(kredi_tab_frame);
kredi_liste_frame.pack(fill='both', expand=True, pady=5)
kredi_tree = tb.Treeview(kredi_liste_frame, columns=('onay', 'vade', 'banka', 'aciklama', 'tutar', 'durum'), show='headings');
kredi_tree.pack(side='left', fill='both', expand=True);
kredi_tree.bind("<Button-1>", on_kredi_taksit_click);
kredi_scrollbar = tb.Scrollbar(kredi_liste_frame, orient=VERTICAL, command=kredi_tree.yview);
kredi_tree.configure(yscroll=kredi_scrollbar.set);
kredi_scrollbar.pack(side=RIGHT, fill=Y);
kredi_tree.tag_configure('odendi', background=style.colors.success);
kredi_tree.tag_configure('odenmedi', background=style.colors.danger);
kredi_tree.heading('onay', text='Öde');
kredi_tree.column('onay', width=45, anchor='center');
kredi_tree.heading('vade', text='Vade Tarihi');
kredi_tree.column('vade', width=100, anchor='center');
kredi_tree.heading('banka', text='Banka');
kredi_tree.column('banka', width=180);
kredi_tree.heading('aciklama', text='Kredi Açıklaması');
kredi_tree.column('aciklama', width=300);
kredi_tree.heading('tutar', text='Taksit Tutarı');
kredi_tree.column('tutar', width=120, anchor='e');
kredi_tree.heading('durum', text='Durum');
kredi_tree.column('durum', width=100, anchor='center')

notebook.add(cek_senet_tab_frame, text='Çek / Senet')
cs_ust_frame = tb.Frame(cek_senet_tab_frame);
cs_ust_frame.pack(fill='x', pady=5)
tb.Label(cs_ust_frame, text="Duruma Göre Filtrele:").pack(side='left', padx=(0, 5))
filtre_cb = tb.Combobox(cs_ust_frame, values=["Tümü", "Portföyde", "Tahsil Edildi", "Ödendi", "Ciro Edildi", "Karşılıksız"], state='readonly', width=20);
filtre_cb.pack(side='left');
filtre_cb.set("Tümü")
tb.Button(cs_ust_frame, text="Filtrele", command=lambda: cek_senet_tablosunu_yenile(filtre_cb.get()), bootstyle="info").pack(side='left', padx=5)
tb.Button(cs_ust_frame, text="Seçili Kaydı Sil", command=cek_senet_sil_logigi, bootstyle="danger-outline").pack(side='left', padx=5)
tb.Button(cs_ust_frame, text="Durum Güncelle", command=durum_guncelle_penceresi_ac, bootstyle="secondary-outline").pack(side='left', padx=5)
cs_liste_frame = tb.Frame(cek_senet_tab_frame);
cs_liste_frame.pack(fill='both', expand=True, pady=5)
cek_senet_tree = tb.Treeview(cs_liste_frame, columns=('onay', 'vade', 'tip', 'taraf', 'tutar', 'durum', 'banka', 'cek_no'), show='headings');
cek_senet_tree.pack(side='left', fill='both', expand=True)
cs_scrollbar = tb.Scrollbar(cs_liste_frame, orient=VERTICAL, command=cek_senet_tree.yview);
cek_senet_tree.configure(yscroll=cs_scrollbar.set);
cs_scrollbar.pack(side=RIGHT, fill=Y)
cek_senet_tree.bind("<Button-1>", on_cek_senet_click)
cek_senet_tree.tag_configure('odendi', background=style.colors.success);
cek_senet_tree.tag_configure('odenmedi', background=style.colors.danger)
cek_senet_tree.heading('onay', text='Onayla');
cek_senet_tree.column('onay', width=45, anchor='center');
cek_senet_tree.heading('vade', text='Vade');
cek_senet_tree.column('vade', width=85);
cek_senet_tree.heading('tip', text='Tip');
cek_senet_tree.column('tip', width=100);
cek_senet_tree.heading('taraf', text='Keşideci/Lehtar');
cek_senet_tree.column('taraf', width=200);
cek_senet_tree.heading('tutar', text='Tutar');
cek_senet_tree.column('tutar', width=120, anchor='e');
cek_senet_tree.heading('durum', text='Durum');
cek_senet_tree.column('durum', width=100, anchor='center');
cek_senet_tree.heading('banka', text='Banka');
cek_senet_tree.column('banka', width=150);
cek_senet_tree.heading('cek_no', text='Çek No');
cek_senet_tree.column('cek_no', width=90)

notebook.add(kk_tab_frame, text='Kredi Kartları')
kk_ust_frame = tb.Frame(kk_tab_frame);
kk_ust_frame.pack(fill='x', pady=5)
tb.Label(kk_ust_frame, text="Duruma Göre Filtrele:").pack(side='left', padx=(0, 5))
kk_filtre_cb = tb.Combobox(kk_ust_frame, values=["Tümü", "Ödenecek", "Kısmi Ödendi", "Tamamen Ödendi"], state='readonly', width=20);
kk_filtre_cb.pack(side='left');
kk_filtre_cb.set("Tümü")
tb.Button(kk_ust_frame, text="Filtrele", command=lambda: kk_harcama_tablosunu_yenile(kk_filtre_cb.get()), bootstyle="info").pack(side='left', padx=5)
tb.Button(kk_ust_frame, text="Seçili Harcamayı Sil", command=kk_harcamasi_sil_logigi, bootstyle="danger-outline").pack(side='left', padx=5)
kk_liste_frame = tb.Frame(kk_tab_frame);
kk_liste_frame.pack(fill='both', expand=True, pady=5)
kk_tree = tb.Treeview(kk_liste_frame, columns=('onay', 'son_odeme', 'kart_adi', 'tutar', 'kalan', 'aciklama', 'islem_tarihi', 'durum'), show='headings');
kk_tree.pack(side='left', fill='both', expand=True)
kk_tree.bind("<Button-1>", on_kk_click)
kk_scrollbar = tb.Scrollbar(kk_liste_frame, orient=VERTICAL, command=kk_tree.yview);
kk_tree.configure(yscroll=kk_scrollbar.set);
kk_scrollbar.pack(side=RIGHT, fill=Y)
kk_tree.tag_configure('odendi', background=style.colors.success);
kk_tree.tag_configure('odenmedi', background=style.colors.danger)
kk_tree.heading('onay', text='Öde');
kk_tree.column('onay', width=45, anchor='center');
kk_tree.heading('son_odeme', text='Son Ödeme');
kk_tree.column('son_odeme', width=90);
kk_tree.heading('kart_adi', text='Kart Adı');
kk_tree.column('kart_adi', width=150);
kk_tree.heading('tutar', text='Toplam Borç');
kk_tree.column('tutar', width=120, anchor='e');
kk_tree.heading('kalan', text='Kalan Borç');
kk_tree.column('kalan', width=120, anchor='e');
kk_tree.heading('aciklama', text='Açıklama');
kk_tree.column('aciklama', width=250);
kk_tree.heading('durum', text='Durum');
kk_tree.column('durum', width=100, anchor='center');
kk_tree.heading('islem_tarihi', text='İşlem Tarihi');
kk_tree.column('islem_tarihi', width=90, anchor='center')

notebook.add(efatura_tab_frame, text='🧾 e-Fatura')
efatura_notebook = tb.Notebook(efatura_tab_frame)
efatura_notebook.pack(pady=5, padx=5, fill="both", expand=True)

# --- Gelen Faturalar Sekmesi ---
gelen_tab = tb.Frame(efatura_notebook, padding=5)
efatura_notebook.add(gelen_tab, text='Gelen Faturalar')

# === SIRALAMA FONKSİYONU ===
def sort_by_column(tree, col, reverse):
    """Treeview'i belirtilen kolona göre sıralar."""
    try:
        # Verileri ve item ID'lerini al
        data = []
        for item_id in tree.get_children(''):
            # Kolon adını kullanarak değeri al
            col_index = tree['columns'].index(col)
            value = tree.item(item_id)['values'][col_index]
            data.append((value, item_id))

        # Veri tipine göre sıralama
        if col == "tutar":
            # "1.234,56 TL" formatını float'a çevirerek sırala
            data.sort(key=lambda t: float(str(t[0]).replace(' TL', '').replace('.', '').replace(',', '.')), reverse=reverse)
        elif col == "tarih":
            # Tarih formatı YYYY-MM-DD olduğu için metin sıralaması doğru çalışır
            data.sort(key=lambda t: str(t[0]), reverse=reverse)
        else:
            # Genel metin sıralaması (küçük/büyük harf duyarsız)
            data.sort(key=lambda t: str(t[0]).lower(), reverse=reverse)

        # Sıralanmış verileri Treeview'e yeniden yerleştir
        for index, (val, item_id) in enumerate(data):
            tree.move(item_id, '', index)

        # Sıralama yönünü tersine çevirmek için komutu güncelle
        tree.heading(col, command=lambda: sort_by_column(tree, col, not reverse))
    except Exception as e:
        print(f"Sıralama sırasında hata: {e}")


gelen_ust_frame = tb.Frame(gelen_tab)
gelen_ust_frame.pack(fill='x', pady=5)

tb.Label(gelen_ust_frame, text="Başlangıç:").pack(side='left', padx=(5,2))
gelen_bas_tarih_entry = tb.DateEntry(gelen_ust_frame, width=12, dateformat='%Y-%m-%d')
gelen_bas_tarih_entry.pack(side='left', padx=(0,10))
gelen_bas_tarih_entry.set_date(date.today().replace(day=1))

tb.Label(gelen_ust_frame, text="Bitiş:").pack(side='left', padx=(5,2))
gelen_bit_tarih_entry = tb.DateEntry(gelen_ust_frame, width=12, dateformat='%Y-%m-%d')
gelen_bit_tarih_entry.pack(side='left', padx=(0,10))
gelen_bit_tarih_entry.set_date(date.today())

tb.Button(gelen_ust_frame, text="📥 Sorgula",
          command=lambda: gelen_faturalari_sorgula_ve_goster(gelen_bas_tarih_entry.get_date(), gelen_bit_tarih_entry.get_date()),
          bootstyle="primary").pack(side='left', padx=5)

tb.Button(gelen_ust_frame, text="✅ Seçili Faturayı İşle",
          command=secili_faturayi_isle_penceresi_ac,
          bootstyle="success-outline").pack(side='left', padx=5)

tb.Button(gelen_ust_frame, text="📂 Fatura Dosyalarını İndir",
          command=secili_faturayi_indir_ve_ac,
          bootstyle="secondary-outline").pack(side='left', padx=5)

tb.Button(gelen_ust_frame, text="📦 Seçilileri Toplu Alış Olarak Aktar",
          command=secili_faturalari_toplu_alis_olarak_aktar,
          bootstyle="info-outline").pack(side='left', padx=5)


gelen_liste_frame = tb.LabelFrame(gelen_tab, text="Gelen E-Faturalar", padding=5)
gelen_liste_frame.pack(fill='both', expand=True, pady=5)

# ONAY KUTUSU İÇİN YENİ KOLON EKLENDİ ('sec')
efatura_tree_columns = ('sec', 'tarih', 'gonderen', 'fatura_no', 'tutar', 'durum')
# CTRL İLE SEÇİM YERİNE KUTUCUKLARI KULLANMAK İÇİN selectmode='none' YAPILDI
efatura_tree = tb.Treeview(gelen_liste_frame, columns=efatura_tree_columns, show='headings', selectmode='none')
efatura_tree.pack(side='left', fill='both', expand=True)
efatura_scrollbar = tb.Scrollbar(gelen_liste_frame, orient=VERTICAL, command=efatura_tree.yview)
efatura_tree.configure(yscroll=efatura_scrollbar.set)
efatura_scrollbar.pack(side=RIGHT, fill=Y)

efatura_tree.tag_configure('islenmis', background=style.colors.success)
# Seçili satırlar için yeni bir tag
efatura_tree.tag_configure('checked', background=style.colors.info)

# KOLON BAŞLIKLARI VE SIRALAMA KOMUTLARI
efatura_tree.heading('sec', text='Seç')
efatura_tree.column('sec', width=40, anchor='center')

# Sıralama komutları eklendi
efatura_tree.heading('tarih', text='Tarih', command=lambda: sort_by_column(efatura_tree, 'tarih', False))
efatura_tree.column('tarih', width=100)

efatura_tree.heading('gonderen', text='Gönderen Unvan', command=lambda: sort_by_column(efatura_tree, 'gonderen', False))
efatura_tree.column('gonderen', width=400)

efatura_tree.heading('fatura_no', text='Fatura No')
efatura_tree.column('fatura_no', width=150)

efatura_tree.heading('tutar', text='Tutar', command=lambda: sort_by_column(efatura_tree, 'tutar', False))
efatura_tree.column('tutar', width=120, anchor='e')

efatura_tree.heading('durum', text='Durum')
efatura_tree.column('durum', width=150, anchor='center')

# === ONAY KUTUSU TIKLAMA FONKSİYONU ===
def toggle_check(event):
    """Onay kutusu kolonuna tıklandığında durumu değiştirir."""
    region = efatura_tree.identify("region", event.x, event.y)
    if region != "cell":
        return

    column = efatura_tree.identify_column(event.x)
    # Sadece ilk kolona ('sec') tıklandığında çalış
    if column == '#1':
        item_id = efatura_tree.identify_row(event.y)
        if not item_id:
            return

        current_tags = set(efatura_tree.item(item_id, "tags"))
        current_values = list(efatura_tree.item(item_id, "values"))

        if 'checked' in current_tags:
            current_tags.remove('checked')
            current_values[0] = "☐" # Boş kutu
        else:
            current_tags.add('checked')
            current_values[0] = "☑" # İşaretli kutu

        # 'islenmis' tag'inin korunmasını sağla
        if 'islenmis' in efatura_tree.item(item_id, "tags"):
             current_tags.add('islenmis')

        efatura_tree.item(item_id, tags=list(current_tags), values=tuple(current_values))

# Tıklama olayını Treeview'e bağla
efatura_tree.bind("<Button-1>", toggle_check)
# --- Giden Faturalar Sekmesi ---
giden_tab = tb.Frame(efatura_notebook, padding=10)
efatura_notebook.add(giden_tab, text='Giden Faturalar')

giden_ust_frame = tb.Frame(giden_tab)
giden_ust_frame.pack(fill='x', pady=5)

tb.Label(giden_ust_frame, text="Başlangıç:").pack(side='left', padx=(5,2))
giden_bas_tarih_entry = tb.DateEntry(giden_ust_frame, width=12, dateformat='%Y-%m-%d')
giden_bas_tarih_entry.pack(side='left', padx=(0,10))
giden_bas_tarih_entry.set_date(date.today().replace(day=1))

tb.Label(giden_ust_frame, text="Bitiş:").pack(side='left', padx=(5,2))
giden_bit_tarih_entry = tb.DateEntry(giden_ust_frame, width=12, dateformat='%Y-%m-%d')
giden_bit_tarih_entry.pack(side='left', padx=(0,10))
giden_bit_tarih_entry.set_date(date.today())

tb.Button(giden_ust_frame, text="📤 Sorgula",
          command=lambda: giden_faturalari_sorgula_ve_goster(giden_bas_tarih_entry.get_date(), giden_bit_tarih_entry.get_date()),
          bootstyle="info").pack(side='left', padx=5)

tb.Button(giden_ust_frame, text="✅ Seçili Faturayı İçe Aktar",
          command=giden_faturayi_ice_aktar_penceresi_ac,
          bootstyle="success-outline").pack(side='left', padx=5)
tb.Button(giden_ust_frame, text="📂 Faturayı Görüntüle",
          command=secili_giden_faturayi_goruntule,
          bootstyle="secondary-outline").pack(side='left', padx=5)

giden_liste_frame = tb.LabelFrame(giden_tab, text="Giden E-Faturalar", padding=5)
giden_liste_frame.pack(fill='both', expand=True, pady=5)
giden_efatura_tree = tb.Treeview(giden_liste_frame, columns=('tarih', 'alici', 'fatura_no', 'tutar', 'durum'), show='headings')
giden_efatura_tree.pack(side='left', fill='both', expand=True)
giden_efatura_scrollbar = tb.Scrollbar(giden_liste_frame, orient=VERTICAL, command=giden_efatura_tree.yview)
giden_efatura_tree.configure(yscroll=giden_efatura_scrollbar.set)
giden_efatura_scrollbar.pack(side=RIGHT, fill=Y)
giden_efatura_tree.tag_configure('islenmis', background=style.colors.success)
giden_efatura_tree.heading('tarih', text='Tarih'); giden_efatura_tree.column('tarih', width=100)
giden_efatura_tree.heading('alici', text='Alıcı Unvan'); giden_efatura_tree.column('alici', width=400)
giden_efatura_tree.heading('fatura_no', text='Fatura No'); giden_efatura_tree.column('fatura_no', width=150)
giden_efatura_tree.heading('tutar', text='Tutar'); giden_efatura_tree.column('tutar', width=120, anchor='e')
giden_efatura_tree.heading('durum', text='Durum'); giden_efatura_tree.column('durum', width=150, anchor='center')

# === 5. PROGRAM BAŞLANGICI ===
def ilk_yukleme():
    yenile_tum_tablolar()
    paneli_yenile()
    finansal_durum_raporla()


pencere.after(100, ilk_yukleme)
pencere.mainloop()