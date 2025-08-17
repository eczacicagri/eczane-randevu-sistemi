# veritabani_yonetimi.py (Finansal Özet ve PyInstaller Uyumlu Final Sürüm)

import sqlite3
from datetime import date
from dateutil.relativedelta import relativedelta
import xml.etree.ElementTree as ET
import sys
import os

def resource_path(relative_path):
    """ Programın hem normal modda hem de .exe olarak çalışırken
        yan dosyaları (veritabanı, ayar dosyası vb.) bulmasını sağlar. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

DB_FILE = resource_path('ruya_eczane.db')

def veritabani_baglan():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

def tarih_araligina_gore_toplam_alis_getir(baslangic_tarihi, bitis_tarihi):
    """Belirtilen tarih aralığındaki depo alışlarını tedarikçiye göre gruplayarak toplarını döndürür."""
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = """
            SELECT
                c.unvan AS aciklama,
                SUM(f.genel_toplam) AS tutar
            FROM Faturalar f
            JOIN Cariler c ON f.cari_id = c.cari_id
            WHERE f.tip = 'Alış' AND f.tarih BETWEEN ? AND ?
            GROUP BY c.unvan
            ORDER BY tutar DESC
        """
        cursor.execute(query, (baslangic_tarihi, bitis_tarihi))
        return cursor.fetchall()
    except Exception as e:
        print(f"Tedarikçiye göre toplu alışlar getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def finansal_ozet_getir(baslangic_tarihi, bitis_tarihi):
    """Belirtilen tarih aralığındaki tüm gelir ve gider kalemlerini toplar."""
    conn = veritabani_baglan()
    if conn is None: return {'gelirler': [], 'giderler': []}
    
    cursor = conn.cursor()
    sonuclar = {'gelirler': [], 'giderler': []}

    try:
        gelir_sorgusu = """
            SELECT tarih, 'Kurumsal Satış' as tip, satis_tipi as aciklama, genel_toplam as tutar FROM KurumsalSatislar WHERE tarih BETWEEN ? AND ?
            UNION ALL
            SELECT tarih, 'Günlük Kasa' as tip, 'Nakit/Kart Toplamı' as aciklama, toplam_tutar as tutar FROM GunlukKasa WHERE tarih BETWEEN ? AND ?
            UNION ALL
            SELECT vade_tarihi as tarih, 'Alınan Çek' as tip, kesideci_lehtar as aciklama, tutar FROM CekSenetler WHERE tip IN ('Alınan Çek', 'Alınan Senet') AND vade_tarihi BETWEEN ? AND ?
        """
        params_gelir = (baslangic_tarihi, bitis_tarihi) * 3 
        cursor.execute(gelir_sorgusu, params_gelir)
        # Fetchall'dan dönen sqlite3.Row nesnelerini dict'e çeviriyoruz
        sonuclar['gelirler'] = [dict(row) for row in cursor.fetchall()]

        gider_sorgusu = """
            SELECT tarih, 'Genel Gider' as tip, kategori as aciklama, toplam_tutar as tutar FROM Giderler WHERE tarih BETWEEN ? AND ?
            UNION ALL
            SELECT vade_tarihi as tarih, 'Verilen Çek' as tip, kesideci_lehtar as aciklama, tutar FROM CekSenetler WHERE tip IN ('Verilen Çek', 'Verilen Senet') AND vade_tarihi BETWEEN ? AND ?
            UNION ALL
            SELECT son_odeme_tarihi as tarih, 'Kredi Kartı Borcu' as tip, kart_adi || ' - ' || harcama_aciklamasi as aciklama, tutar FROM KrediKartiHarcamalari WHERE son_odeme_tarihi BETWEEN ? AND ?
            UNION ALL
            SELECT vade_tarihi as tarih, 'Banka Kredisi Taksiti' as tip, banka_adi || ' - ' || kredi_aciklamasi as aciklama, taksit_tutari as tutar FROM KrediTaksitleri t JOIN BankaKredileri k ON t.kredi_id = k.kredi_id WHERE t.vade_tarihi BETWEEN ? AND ?
        """
        params_gider = (baslangic_tarihi, bitis_tarihi) * 4
        cursor.execute(gider_sorgusu, params_gider)
        sonuclar['giderler'] = [dict(row) for row in cursor.fetchall()]
        
        # Depo Alışlarını tedarikçiye göre özetleyerek giderlere ekle
        toplam_alislar = tarih_araligina_gore_toplam_alis_getir(baslangic_tarihi, bitis_tarihi)
        for alis in toplam_alislar:
            sonuclar['giderler'].append({
                'tarih': bitis_tarihi, 
                'tip': 'Depo Alış Özeti',
                'aciklama': alis['aciklama'],
                'tutar': alis['tutar']
            })

        return sonuclar
        
    except Exception as e:
        print(f"Finansal özet getirilirken hata: {e}")
        return {'gelirler': [], 'giderler': []}
    finally:
        conn.close()

# --- (Diğer tüm fonksiyonlarınız olduğu gibi buraya gelecek) ---
# Lütfen bu dosyanın geri kalanının kendi dosyanızdaki gibi
# tam olduğundan emin olun. Aşağıda tam listeyi bulabilirsiniz.

def ilk_kurulum():
    conn = veritabani_baglan()
    if conn is None: return
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS Cariler (cari_id INTEGER PRIMARY KEY, unvan TEXT NOT NULL UNIQUE, vergi_no TEXT, adres TEXT, telefon TEXT, tip TEXT NOT NULL)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faturalar (
            fatura_id INTEGER PRIMARY KEY, fatura_no TEXT NOT NULL, cari_id INTEGER, tarih TEXT NOT NULL, 
            tip TEXT NOT NULL, ara_toplam REAL, kdv_toplam REAL, genel_toplam REAL, 
            odeme_durumu TEXT DEFAULT 'Ödenmedi', efatura_uuid TEXT UNIQUE, efatura_durum TEXT,
            kaynak TEXT DEFAULT 'Manuel', FOREIGN KEY (cari_id) REFERENCES Cariler (cari_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Giderler (
            gider_id INTEGER PRIMARY KEY, tarih TEXT NOT NULL, kategori TEXT NOT NULL, aciklama TEXT,
            ara_toplam REAL NOT NULL, kdv_tutari REAL DEFAULT 0, toplam_tutar REAL NOT NULL,
            efatura_uuid TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS KurumsalSatislar (
            id INTEGER PRIMARY KEY, tarih TEXT NOT NULL, satis_tipi TEXT NOT NULL, 
            kdv1 REAL DEFAULT 0, kdv10 REAL DEFAULT 0, kdv20 REAL DEFAULT 0, 
            kdv_toplam REAL NOT NULL, genel_toplam REAL NOT NULL, aciklama TEXT,
            efatura_uuid TEXT
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS CekSenetler (id INTEGER PRIMARY KEY, tip TEXT NOT NULL, vade_tarihi TEXT NOT NULL, duzenleme_tarihi TEXT NOT NULL, tutar REAL NOT NULL, kesideci_lehtar TEXT NOT NULL, banka TEXT, cek_no TEXT, durum TEXT NOT NULL, aciklama TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS KrediKartiHarcamalari (id INTEGER PRIMARY KEY, kart_adi TEXT NOT NULL, harcama_aciklamasi TEXT, tutar REAL NOT NULL, kalan_borc REAL NOT NULL, islem_tarihi TEXT NOT NULL, son_odeme_tarihi TEXT NOT NULL, odeme_durumu TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS KrediKartiOdemeleri (odeme_id INTEGER PRIMARY KEY, harcama_id INTEGER NOT NULL, odeme_tarihi TEXT NOT NULL, odenen_tutar REAL NOT NULL, FOREIGN KEY (harcama_id) REFERENCES KrediKartiHarcamalari (id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS GunlukKasa (id INTEGER PRIMARY KEY, tarih TEXT NOT NULL UNIQUE, nakit_tutar REAL NOT NULL DEFAULT 0, kart_tutar REAL NOT NULL DEFAULT 0, toplam_tutar REAL NOT NULL DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Z_Raporlari (id INTEGER PRIMARY KEY, tarih TEXT NOT NULL UNIQUE, toplam_tutar REAL NOT NULL, kdv1 REAL NOT NULL DEFAULT 0, kdv10 REAL NOT NULL DEFAULT 0, kdv20 REAL NOT NULL DEFAULT 0, kdv_toplam REAL NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS BankaKredileri (kredi_id INTEGER PRIMARY KEY, banka_adi TEXT NOT NULL, kredi_aciklamasi TEXT, cekme_tarihi TEXT NOT NULL, taksit_sayisi INTEGER NOT NULL, aylik_taksit_tutari REAL NOT NULL, toplam_geri_odeme REAL NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS KrediTaksitleri (taksit_id INTEGER PRIMARY KEY, kredi_id INTEGER NOT NULL, vade_tarihi TEXT NOT NULL, taksit_tutari REAL NOT NULL, durum TEXT NOT NULL, FOREIGN KEY (kredi_id) REFERENCES BankaKredileri (kredi_id) ON DELETE CASCADE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS KasaHesaplamalari (hesap_id INTEGER PRIMARY KEY, tarih TEXT NOT NULL UNIQUE, baslangic_tutari REAL NOT NULL DEFAULT 0, sistem_nakit_geliri REAL NOT NULL DEFAULT 0, kasadan_cikis_toplami REAL NOT NULL DEFAULT 0, beklenen_nakit REAL NOT NULL DEFAULT 0, sayilan_nakit REAL NOT NULL DEFAULT 0, fark REAL NOT NULL DEFAULT 0, durum TEXT, aciklama TEXT)")
    conn.commit()
    conn.close()

def toplu_alis_listesi_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try: 
        query = "SELECT f.fatura_id, f.tarih, f.fatura_no, c.unvan, f.kdv_toplam, f.genel_toplam FROM Faturalar f JOIN Cariler c ON f.cari_id = c.cari_id WHERE f.tip = 'Alış' ORDER BY f.tarih DESC"
        cursor.execute(query) 
        return cursor.fetchall()
    except Exception as e:
        print(f"Toplu Alış listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def toplu_alis_ekle(fatura_no, cari_unvan, tarih, genel_toplam, kdv1, kdv10, kdv20):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cari_id FROM Cariler WHERE unvan = ?", (cari_unvan,))
        cari_data = cursor.fetchone()
        if cari_data: cari_id = cari_data['cari_id']
        else:
            cursor.execute("INSERT INTO Cariler (unvan, tip) VALUES (?, ?)", (cari_unvan, 'Satıcı'))
            cari_id = cursor.lastrowid
        kdv_toplam = kdv1 + kdv10 + kdv20
        ara_toplam = genel_toplam - kdv_toplam
        cursor.execute("INSERT INTO Faturalar (fatura_no, cari_id, tarih, tip, ara_toplam, kdv_toplam, genel_toplam) VALUES (?, ?, ?, ?, ?, ?, ?)", (fatura_no, cari_id, tarih, 'Alış', round(ara_toplam,2), round(kdv_toplam,2), round(genel_toplam,2)))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"TOPLU ALIŞ EKLEME HATASI: {e}")
        return False
    finally:
        conn.close()

def toplu_alis_sil(fatura_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Faturalar WHERE fatura_id = ?", (fatura_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"TOPLU ALIŞ SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
def kurumsal_satis_ekle(tarih, satis_tipi, genel_toplam, kdv1, kdv10, kdv20, aciklama):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        kdv_toplam = kdv1 + kdv10 + kdv20
        cursor.execute("INSERT INTO KurumsalSatislar (tarih, satis_tipi, kdv1, kdv10, kdv20, kdv_toplam, genel_toplam, aciklama) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (tarih, satis_tipi, kdv1, kdv10, kdv20, round(kdv_toplam, 2), round(genel_toplam, 2), aciklama))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"KURUMSAL SATIŞ EKLEME HATASI: {e}")
        return False
    finally:
        conn.close()

def kurumsal_satis_listesi_getir(filtre=None):
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT id, tarih, satis_tipi, genel_toplam, aciklama FROM KurumsalSatislar"
        if filtre and filtre != "Tümü":
            query += f" WHERE satis_tipi = '{filtre}'"
        query += " ORDER BY tarih DESC"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Kurumsal Satış listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def kurumsal_satis_sil(satis_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM KurumsalSatislar WHERE id = ?", (satis_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"KURUMSAL SATIŞ SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
def gider_ekle(tarih, kategori, aciklama, ara_toplam, kdv_tutari=0):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        toplam_tutar = ara_toplam + kdv_tutari
        cursor.execute("INSERT INTO Giderler (tarih, kategori, aciklama, ara_toplam, kdv_tutari, toplam_tutar) VALUES (?, ?, ?, ?, ?, ?)", (tarih, kategori, aciklama, ara_toplam, kdv_tutari, toplam_tutar))
        conn.commit()
        return True
    except Exception as e:
        print(f"GİDER EKLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def gider_listesi_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT gider_id, tarih, kategori, aciklama, toplam_tutar FROM Giderler ORDER BY tarih DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"Gider listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def gider_sil(gider_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Giderler WHERE gider_id = ?", (gider_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"GİDER SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kdv_raporu_getir(baslangic_tarihi, bitis_tarihi):
    rapor = {'hesaplanan_kdv': 0.0, 'indirilecek_kdv_alis': 0.0, 'indirilecek_kdv_gider': 0.0}
    conn = veritabani_baglan()
    if conn is None: return rapor
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SUM(kdv_toplam) FROM KurumsalSatislar WHERE tarih BETWEEN ? AND ?", (baslangic_tarihi, bitis_tarihi))
        sonuc_kurumsal = cursor.fetchone()
        hesaplanan_kdv_kurumsal = (sonuc_kurumsal[0] if sonuc_kurumsal and sonuc_kurumsal[0] is not None else 0.0)

        cursor.execute("SELECT SUM(kdv_toplam) FROM Z_Raporlari WHERE tarih BETWEEN ? AND ?", (baslangic_tarihi, bitis_tarihi))
        sonuc_z_raporu = cursor.fetchone()
        hesaplanan_kdv_z_raporu = (sonuc_z_raporu[0] if sonuc_z_raporu and sonuc_z_raporu[0] is not None else 0.0)
        
        rapor['hesaplanan_kdv'] = float(hesaplanan_kdv_kurumsal + hesaplanan_kdv_z_raporu)
        
        cursor.execute("SELECT SUM(kdv_toplam) FROM Faturalar WHERE tip = 'Alış' AND tarih BETWEEN ? AND ?", (baslangic_tarihi, bitis_tarihi))
        sonuc_alis = cursor.fetchone()
        if sonuc_alis and sonuc_alis[0] is not None: rapor['indirilecek_kdv_alis'] = float(sonuc_alis[0])
        
        cursor.execute("SELECT SUM(kdv_tutari) FROM Giderler WHERE tarih BETWEEN ? AND ?", (baslangic_tarihi, bitis_tarihi))
        sonuc_gider = cursor.fetchone()
        if sonuc_gider and sonuc_gider[0] is not None: rapor['indirilecek_kdv_gider'] = float(sonuc_gider[0])
        
        return rapor
    except Exception as e:
        print(f"KDV Raporu hatası: {e}")
        return rapor
    finally:
        conn.close()

def kategoriye_gore_gider_getir(bas_tarih=None, bit_tarih=None):
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT kategori, SUM(toplam_tutar) as toplam FROM Giderler"
        params = []
        if bas_tarih and bit_tarih:
            query += " WHERE tarih BETWEEN ? AND ?"
            params.extend([bas_tarih, bit_tarih])
        query += " GROUP BY kategori"
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Kategoriye göre giderler getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def tipe_gore_satis_getir(bas_tarih=None, bit_tarih=None):
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT satis_tipi, SUM(genel_toplam) as toplam FROM KurumsalSatislar"
        params = []
        if bas_tarih and bit_tarih:
            query += " WHERE tarih BETWEEN ? AND ?"
            params.extend([bas_tarih, bit_tarih])
        query += " GROUP BY satis_tipi"
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Tipe göre satışlar getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def cek_senet_ekle(tip, vade_tarihi, duzenleme_tarihi, tutar, kesideci_lehtar, banka, cek_no, durum, aciklama):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO CekSenetler (tip, vade_tarihi, duzenleme_tarihi, tutar, kesideci_lehtar, banka, cek_no, durum, aciklama) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",(tip, vade_tarihi, duzenleme_tarihi, tutar, kesideci_lehtar, banka, cek_no, durum, aciklama))
        conn.commit()
        return True
    except Exception as e:
        print(f"ÇEK/SENET EKLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def cek_senet_listesi_getir(filtre=None):
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM CekSenetler"
        if filtre and filtre != "Tümü": query += f" WHERE durum = '{filtre}'"
        query += " ORDER BY vade_tarihi ASC"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Çek/Senet listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def cek_senet_durum_guncelle(kayit_id, yeni_durum):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE CekSenetler SET durum = ? WHERE id = ?", (yeni_durum, kayit_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"ÇEK/SENET GÜNCELLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
def cek_senet_sil(kayit_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM CekSenetler WHERE id = ?", (kayit_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"ÇEK/SENET SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_karti_harcamasi_ekle(kart_adi, aciklama, tutar, islem_tarihi, son_odeme_tarihi):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO KrediKartiHarcamalari (kart_adi, harcama_aciklamasi, tutar, kalan_borc, islem_tarihi, son_odeme_tarihi, odeme_durumu) VALUES (?, ?, ?, ?, ?, ?, ?)", (kart_adi, aciklama, tutar, tutar, islem_tarihi, son_odeme_tarihi, "Ödenecek"))
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ KARTI HARCAMASI EKLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_karti_harcamalari_getir(filtre=None):
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM KrediKartiHarcamalari"
        if filtre and filtre != "Tümü": query += f" WHERE odeme_durumu = '{filtre}'"
        query += " ORDER BY son_odeme_tarihi ASC"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Kredi Kartı harcamaları getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def kk_odeme_yap(harcama_id, odeme_tutari):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT kalan_borc FROM KrediKartiHarcamalari WHERE id = ?", (harcama_id,))
        mevcut_kalan_borc = cursor.fetchone()[0]
        yeni_kalan_borc = mevcut_kalan_borc - odeme_tutari
        yeni_durum = "Kısmi Ödendi"
        if yeni_kalan_borc <= 0:
            yeni_kalan_borc = 0
            yeni_durum = "Tamamen Ödendi"
        cursor.execute("UPDATE KrediKartiHarcamalari SET kalan_borc = ?, odeme_durumu = ? WHERE id = ?", (yeni_kalan_borc, yeni_durum, harcama_id))
        odeme_tarihi = date.today().strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO KrediKartiOdemeleri (harcama_id, odeme_tarihi, odenen_tutar) VALUES (?, ?, ?)", (harcama_id, odeme_tarihi, odeme_tutari))
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ KARTI ÖDEME YAPMA HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_karti_harcamasi_sil(harcama_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM KrediKartiOdemeleri WHERE harcama_id = ?", (harcama_id,))
        cursor.execute("DELETE FROM KrediKartiHarcamalari WHERE id = ?", (harcama_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ KARTI SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def gunluk_kasa_kaydet(tarih, nakit, kart):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        toplam = nakit + kart
        query = """
            INSERT INTO GunlukKasa (tarih, nakit_tutar, kart_tutar, toplam_tutar)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tarih) DO UPDATE SET
                nakit_tutar = excluded.nakit_tutar,
                kart_tutar = excluded.kart_tutar,
                toplam_tutar = excluded.toplam_tutar
        """
        cursor.execute(query, (tarih, nakit, kart, toplam))
        conn.commit()
        return True
    except Exception as e:
        print(f"GÜNLÜK KASA KAYDETME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def aylik_kasa_raporu_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = """
            SELECT
                strftime('%Y-%m', tarih) as ay,
                SUM(nakit_tutar) as toplam_nakit,
                SUM(kart_tutar) as toplam_kart,
                SUM(toplam_tutar) as genel_toplam
            FROM GunlukKasa
            GROUP BY ay
            ORDER BY ay DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Aylık kasa raporu getirilirken hata: {e}")
        return []
    finally:
        conn.close()
        
def gunluk_kasa_listesi_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT tarih, nakit_tutar, kart_tutar, toplam_tutar FROM GunlukKasa ORDER BY tarih DESC"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Günlük kasa listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def gunluk_kasa_sil(tarih):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM GunlukKasa WHERE tarih = ?", (tarih,))
        conn.commit()
        return True
    except Exception as e:
        print(f"GÜNLÜK KASA SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def z_raporu_ekle(tarih, toplam_tutar, kdv1, kdv10, kdv20):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        kdv_toplam = kdv1 + kdv10 + kdv20
        query = """
            INSERT INTO Z_Raporlari (tarih, toplam_tutar, kdv1, kdv10, kdv20, kdv_toplam)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tarih) DO UPDATE SET
                toplam_tutar = excluded.toplam_tutar,
                kdv1 = excluded.kdv1,
                kdv10 = excluded.kdv10,
                kdv20 = excluded.kdv20,
                kdv_toplam = excluded.kdv_toplam
        """
        cursor.execute(query, (tarih, toplam_tutar, kdv1, kdv10, kdv20, kdv_toplam))
        conn.commit()
        return True
    except Exception as e:
        print(f"Z RAPORU KAYDETME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def z_raporu_listesi_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM Z_Raporlari ORDER BY tarih DESC"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Z Raporu listesi getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def z_raporu_sil(rapor_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Z_Raporlari WHERE id = ?", (rapor_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Z RAPORU SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_ekle(banka_adi, kredi_aciklamasi, cekme_tarihi, taksit_sayisi, aylik_taksit_tutari):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        toplam_geri_odeme = aylik_taksit_tutari * taksit_sayisi
        cursor.execute("""
            INSERT INTO BankaKredileri (banka_adi, kredi_aciklamasi, cekme_tarihi, taksit_sayisi, aylik_taksit_tutari, toplam_geri_odeme)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (banka_adi, kredi_aciklamasi, cekme_tarihi.strftime('%Y-%m-%d'), taksit_sayisi, aylik_taksit_tutari, toplam_geri_odeme))
        kredi_id = cursor.lastrowid

        for i in range(1, taksit_sayisi + 1):
            vade_tarihi = cekme_tarihi + relativedelta(months=i)
            cursor.execute("""
                INSERT INTO KrediTaksitleri (kredi_id, vade_tarihi, taksit_tutari, durum)
                VALUES (?, ?, ?, ?)
            """, (kredi_id, vade_tarihi.strftime('%Y-%m-%d'), aylik_taksit_tutari, "Ödenecek"))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ EKLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_taksitlerini_getir():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        query = """
            SELECT
                t.taksit_id, t.kredi_id, t.vade_tarihi, t.taksit_tutari, t.durum,
                k.banka_adi, k.kredi_aciklamasi
            FROM KrediTaksitleri t
            JOIN BankaKredileri k ON t.kredi_id = k.kredi_id
            ORDER BY t.vade_tarihi ASC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Kredi taksitleri getirilirken hata: {e}")
        return []
    finally:
        conn.close()

def kredi_taksit_durum_guncelle(taksit_id, yeni_durum):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE KrediTaksitleri SET durum = ? WHERE taksit_id = ?", (yeni_durum, taksit_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ TAKSİT GÜNCELLEME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kredi_sil(kredi_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM BankaKredileri WHERE kredi_id = ?", (kredi_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"KREDİ SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def efatura_ice_aktar(fatura_uuid, fatura_no, cari_unvan, tarih, genel_toplam, kdv_toplam):
    conn = veritabani_baglan()
    if conn is None: return False, "Veritabanı bağlantı hatası."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fatura_id FROM Faturalar WHERE efatura_uuid = ?", (fatura_uuid,))
        if cursor.fetchone(): return False, "Bu fatura zaten daha önce içe aktarılmış."
        cursor.execute("SELECT gider_id FROM Giderler WHERE efatura_uuid = ?", (fatura_uuid,))
        if cursor.fetchone(): return False, "Bu fatura zaten 'Gider' olarak içe aktarılmış."

        cursor.execute("SELECT cari_id FROM Cariler WHERE unvan = ?", (cari_unvan,))
        cari_data = cursor.fetchone()
        if cari_data: cari_id = cari_data['cari_id']
        else:
            cursor.execute("INSERT INTO Cariler (unvan, tip) VALUES (?, ?)", (cari_unvan, 'Satıcı'))
            cari_id = cursor.lastrowid

        ara_toplam = genel_toplam - kdv_toplam

        cursor.execute("""
            INSERT INTO Faturalar
            (fatura_no, cari_id, tarih, tip, ara_toplam, kdv_toplam, genel_toplam, efatura_uuid, efatura_durum, kaynak)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fatura_no, cari_id, tarih, 'Alış', round(ara_toplam,2), round(kdv_toplam,2), round(genel_toplam,2), fatura_uuid, 'İçe Aktarıldı', 'e-Fatura'))

        conn.commit()
        return True, "Fatura başarıyla 'Alış' olarak içe aktarıldı."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, f"UUID '{fatura_uuid}' ile zaten bir kayıt var."
    except Exception as e:
        conn.rollback()
        print(f"E-FATURA İÇE AKTARMA HATASI: {e}")
        return False, f"Beklenmedik bir hata oluştu: {e}"
    finally:
        conn.close()

def efatura_gider_olarak_ice_aktar(fatura_uuid, cari_unvan, tarih, genel_toplam, kdv_toplam, kategori, aciklama):
    conn = veritabani_baglan()
    if conn is None: return False, "Veritabanı bağlantı hatası."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fatura_id FROM Faturalar WHERE efatura_uuid = ?", (fatura_uuid,))
        if cursor.fetchone(): return False, "Bu fatura zaten 'Toplu Alış' olarak içe aktarılmış."
        
        cursor.execute("SELECT gider_id FROM Giderler WHERE efatura_uuid = ?", (fatura_uuid,))
        if cursor.fetchone(): return False, "Bu fatura zaten 'Gider' olarak içe aktarılmış."

        ara_toplam = genel_toplam - kdv_toplam
        full_aciklama = f"{cari_unvan} - {aciklama}".strip()

        cursor.execute("""
            INSERT INTO Giderler
            (tarih, kategori, aciklama, ara_toplam, kdv_tutari, toplam_tutar, efatura_uuid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tarih, kategori, full_aciklama, round(ara_toplam, 2), round(kdv_toplam, 2), round(genel_toplam, 2), fatura_uuid))

        conn.commit()
        return True, "Fatura başarıyla 'Gider' olarak kaydedildi."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, f"UUID '{fatura_uuid}' ile zaten bir kayıt var (Giderler)."
    except Exception as e:
        conn.rollback()
        print(f"E-FATURA GİDER İÇE AKTARMA HATASI: {e}")
        return False, f"Beklenmedik bir hata oluştu: {e}"
    finally:
        conn.close()

def efatura_kurumsal_satis_olarak_ice_aktar(fatura_uuid, fatura_no, alici_unvan, tarih, genel_toplam, kdv_toplam, satis_tipi, aciklama):
    conn = veritabani_baglan()
    if conn is None: return False, "Veritabanı bağlantısı hatası."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM KurumsalSatislar WHERE efatura_uuid = ?", (fatura_uuid,))
        if cursor.fetchone():
            return False, "Bu fatura zaten 'Kurumsal Satış' olarak içe aktarılmış."

        full_aciklama = f"e-Fatura: {alici_unvan} ({fatura_no}) - {aciklama}".strip()
        
        cursor.execute("""
            INSERT INTO KurumsalSatislar
            (tarih, satis_tipi, kdv10, kdv_toplam, genel_toplam, aciklama, efatura_uuid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tarih, satis_tipi, kdv_toplam, kdv_toplam, genel_toplam, full_aciklama, fatura_uuid))

        conn.commit()
        return True, "Giden Fatura başarıyla 'Kurumsal Satış' olarak kaydedildi."
    except Exception as e:
        conn.rollback()
        print(f"E-FATURA KURUMSAL SATIŞ İÇE AKTARMA HATASI: {e}")
        return False, f"Beklenmedik bir hata oluştu: {e}"
    finally:
        conn.close()
    
def kasa_hesabi_getir(tarih_str):
    conn = veritabani_baglan()
    if conn is None: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nakit_tutar FROM GunlukKasa WHERE tarih = ?", (tarih_str,))
        nakit_gelir_sonuc = cursor.fetchone()
        sistem_nakit_geliri = nakit_gelir_sonuc['nakit_tutar'] if nakit_gelir_sonuc else 0.0

        cursor.execute("SELECT * FROM KasaHesaplamalari WHERE tarih = ?", (tarih_str,))
        hesap_verisi = cursor.fetchone()

        if hesap_verisi:
            hesap_dict = dict(hesap_verisi)
            hesap_dict['sistem_nakit_geliri'] = sistem_nakit_geliri
            return hesap_dict
        else:
            return {
                'sistem_nakit_geliri': sistem_nakit_geliri,
                'baslangic_tutari': 0.0,
                'kasadan_cikis_toplami': 0.0,
                'sayilan_nakit': 0.0,
                'aciklama': ''
            }
            
    except Exception as e:
        print(f"Kasa hesabı getirilirken hata: {e}")
        return None
    finally:
        conn.close()


def kasa_hesabi_ekle_guncelle(tarih, baslangic, sistem_nakit, cikis, sayilan, aciklama):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    
    beklenen_nakit = (baslangic + sistem_nakit) - cikis
    fark = sayilan - beklenen_nakit
    
    durum = "Tamam"
    if fark > 0.01:
        durum = f"{fark:,.2f} TL Fazla"
    elif fark < -0.01:
        durum = f"{abs(fark):,.2f} TL Eksik"

    try:
        query = """
            INSERT INTO KasaHesaplamalari (tarih, baslangic_tutari, sistem_nakit_geliri, kasadan_cikis_toplami, beklenen_nakit, sayilan_nakit, fark, durum, aciklama)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tarih) DO UPDATE SET
                baslangic_tutari = excluded.baslangic_tutari,
                sistem_nakit_geliri = excluded.sistem_nakit_geliri,
                kasadan_cikis_toplami = excluded.kasadan_cikis_toplami,
                beklenen_nakit = excluded.beklenen_nakit,
                sayilan_nakit = excluded.sayilan_nakit,
                fark = excluded.fark,
                durum = excluded.durum,
                aciklama = excluded.aciklama
        """
        params = (tarih, baslangic, sistem_nakit, cikis, beklenen_nakit, sayilan, fark, durum, aciklama)
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"KASA HESABI KAYDETME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def kasa_hesaplarini_listele():
    conn = veritabani_baglan()
    if conn is None: return []
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM KasaHesaplamalari ORDER BY tarih DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"Kasa hesapları listelenirken hata: {e}")
        return []
    finally:
        conn.close()

def kasa_hesabi_sil(hesap_id):
    conn = veritabani_baglan()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM KasaHesaplamalari WHERE hesap_id = ?", (hesap_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"KASA HESABI SİLME HATASI: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_imported_fatura_uuids():
    conn = veritabani_baglan()
    if conn is None: return set()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT efatura_uuid FROM Faturalar WHERE efatura_uuid IS NOT NULL")
        return {row['efatura_uuid'] for row in cursor.fetchall()}
    except Exception as e:
        print(f"İçe aktarılmış fatura UUID'leri getirilirken hata: {e}")
        return set()
    finally:
        conn.close()

def get_all_imported_gider_uuids():
    conn = veritabani_baglan()
    if conn is None: return set()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT efatura_uuid FROM Giderler WHERE efatura_uuid IS NOT NULL")
        return {row['efatura_uuid'] for row in cursor.fetchall()}
    except Exception as e:
        print(f"İçe aktarılmış gider UUID'leri getirilirken hata: {e}")
        return set()
    finally:
        conn.close()

def get_all_imported_kurumsal_satis_uuids():
    conn = veritabani_baglan()
    if conn is None: return set()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT efatura_uuid FROM KurumsalSatislar WHERE efatura_uuid IS NOT NULL")
        return {row['efatura_uuid'] for row in cursor.fetchall()}
    except Exception as e:
        print(f"İçe aktarılmış kurumsal satış UUID'leri getirilirken hata: {e}")
        return set()
    finally:
        conn.close()