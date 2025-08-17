# sms_entegrasyonu.py

import requests  # SMS API'leri genellikle HTTP istekleri kullanır
import veritabani_yonetimi
from datetime import date
from ttkbootstrap.dialogs import Messagebox

# --- SMS SAĞLAYICI BİLGİLERİ (KENDİNİZİNKİYLE DEĞİŞTİRİN) ---
# Bu bilgiler genellikle SMS firmanızın size verdiği bilgilerdir.
SMS_API_URL = "https://api.smsfirmasi.com/gonder"  # <<< BURAYA SMS FİRMANIZIN API ADRESİNİ YAZIN
SMS_API_KULLANICI_ADI = "kullanici_adiniz"         # <<< BURAYA KULLANICI ADINIZI YAZIN
SMS_API_SIFRE = "sifreniz"                       # <<< BURAYA ŞİFRENİZİ YAZIN
SMS_GONDEREN_BASLIK = "RUYAECZANE"               # <<< BURAYA GÖNDEREN BAŞLIĞINI YAZIN
# -----------------------------------------------------------------

def gunluk_kasa_raporu_sms_gonder(alici_telefon_no, tarih):
    """Veritabanından belirtilen tarihin kasa durumunu alır ve SMS olarak gönderir."""
    
    # 1. Telefon numarasının geçerli olup olmadığını kontrol et
    if not alici_telefon_no or len(alici_telefon_no) < 10:
        Messagebox.showerror("Hata", "Geçerli bir alıcı telefon numarası girilmedi.")
        return

    # 2. Veritabanından o günün kasa hesabını al
    tarih_str = tarih.strftime('%Y-%m-%d')
    son_hesap = veritabani_yonetimi.kasa_hesabi_getir(tarih_str)

    if not son_hesap or 'fark' not in son_hesap:
        Messagebox.showinfo("Bilgi", f"{tarih_str} tarihi için gönderilecek bir kasa raporu bulunamadı.")
        return

    # 3. SMS Mesajını oluştur
    tarih_formatli = tarih.strftime('%d.%m.%Y')
    durum_mesaji = son_hesap.get('durum', 'Hesaplanmadı')
    
    mesaj = f"Rüya Eczanesi {tarih_formatli} Kasa Raporu:\nDurum: {durum_mesaji}"

    # 4. SMS Gönderme İsteğini Hazırla (Bu bölüm SMS firmanıza göre değişir)
    # Bu genellikle bir JSON veya XML formatında olur.
    # Aşağıdaki `params` sözlüğü yaygın bir örnektir.
    params = {
        'username': SMS_API_KULLANICI_ADI,
        'password': SMS_API_SIFRE,
        'source_addr': SMS_GONDEREN_BASLIK, # Gönderen başlığı
        'dest_addr': alici_telefon_no,      # Alıcı telefon numarası
        'message': mesaj                    # Gönderilecek mesaj
    }

    # 5. SMS API'sine isteği gönder
    try:
        print(f"SMS Gönderiliyor...\nAlıcı: {alici_telefon_no}\nMesaj: {mesaj}")
        
        # response = requests.post(SMS_API_URL, json=params, timeout=10) # API'niz JSON kabul ediyorsa
        response = requests.get(SMS_API_URL, params=params, timeout=10) # API'niz GET parametresi kabul ediyorsa
        
        # Yanıtı kontrol et (Başarılı kodlar genellikle 200, 201, "OK" gibi değerlerdir)
        # Bu kontrolü SMS firmanızın dokümanlarına göre yapmalısınız.
        if response.status_code == 200 and "OK" in response.text:
             Messagebox.showinfo("Başarılı", f"Kasa raporu {alici_telefon_no} numarasına başarıyla gönderildi.")
        else:
            Messagebox.showerror("SMS Gönderim Hatası", f"SMS gönderilemedi.\nAPI Cevabı: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        Messagebox.showerror("Bağlantı Hatası", f"SMS servisine bağlanırken bir hata oluştu: {e}")