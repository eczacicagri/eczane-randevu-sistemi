# ayarlar_yonetimi.py (PyInstaller Uyumlu Sürüm)
import json
import sys
import os

def resource_path(relative_path):
    """ Programın hem normal modda hem de .exe olarak çalışırken
        yan dosyaları (veritabanı, ayar dosyası vb.) bulmasını sağlar. """
    try:
        # PyInstaller geçici bir klasör oluşturur ve yolu _MEIPASS içinde saklar
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

CONFIG_DOSYASI = resource_path('config.json')

def varsayilan_ayarlari_olustur():
    """Varsayılan ayarları içeren bir sözlük döndürür."""
    # ... (Bu fonksiyonun geri kalanı aynı, değişiklik yok) ...
    return {
        "tema": "litera",
        "efatura_kullanici_adi": "HENUZ_GIRILMEDI",
        "efatura_sifre": "HENUZ_GIRILMEDI",
        "custom_tema_renkleri": {
            "bg": "#F0F0F0",
            "fg": "black",
            "entry_bg": "white",
            "accent_bg": "#0078D7",
            "accent_fg": "white",
            "odendi_bg": "#C8E6C9",
            "odenmedi_bg": "#FFCDD2",
            "btn_yesil": "#4CAF50",
            "btn_kirmizi": "#f44336",
            "btn_mavi": "#0078D7",
            "btn_turuncu": "#FF9800",
            "btn_gri": "#607D8B"
        },
        "gider_kategorileri": [
            "Kira", "Maaş", "Fatura (Elektrik, Su, vb.)",
            "Vergi", "Yemek", "Temizlik", "Ofis Malzemesi", "Diğer"
        ],
        "satis_tipleri": [
            "SGK A Grubu", "SGK B Grubu", "SGK C Grubu",
            "Sıralı Dağıtım", "Kan Ürünü", "Farmazon", "Diğer"
        ]
    }

def ayarlari_yukle():
    """config.json dosyasını okur. Dosya yoksa oluşturur ve varsayılan ayarları yükler."""
    try:
        with open(CONFIG_DOSYASI, 'r', encoding='utf-8') as f:
            ayarlar = json.load(f)
            varsayilanlar = varsayilan_ayarlari_olustur()
            guncelleme_yapildi = False
            for anahtar in varsayilanlar:
                if anahtar not in ayarlar:
                    ayarlar[anahtar] = varsayilanlar[anahtar]
                    guncelleme_yapildi = True
            if "custom_tema_renkleri" not in ayarlar:
                ayarlar["custom_tema_renkleri"] = varsayilanlar["custom_tema_renkleri"]
                guncelleme_yapildi = True
            else:
                for renk_anahtari in varsayilanlar["custom_tema_renkleri"]:
                    if renk_anahtari not in ayarlar["custom_tema_renkleri"]:
                        ayarlar["custom_tema_renkleri"][renk_anahtari] = varsayilanlar["custom_tema_renkleri"][renk_anahtari]
                        guncelleme_yapildi = True
            if guncelleme_yapildi:
                ayarlari_kaydet(ayarlar)
            return ayarlar
    except (FileNotFoundError, json.JSONDecodeError):
        ayarlar = varsayilan_ayarlari_olustur()
        ayarlari_kaydet(ayarlar)
        return ayarlar

def ayarlari_kaydet(ayarlar):
    """Verilen ayarlar sözlüğünü config.json dosyasına yazar."""
    try:
        with open(CONFIG_DOSYASI, 'w', encoding='utf-8') as f:
            json.dump(ayarlar, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ayarlar kaydedilirken hata oluştu: {e}")
        return False