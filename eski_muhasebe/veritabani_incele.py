import sqlite3

try:
    # Veritabanı dosyasına bağlan
    con = sqlite3.connect("ruya_eczane.db")
    cur = con.cursor()

    # Tüm tabloların isimlerini al
    res = cur.execute("SELECT name FROM sqlite_master WHERE type='table';")

    print("--- Veritabanı Şeması ---")
    for name in res.fetchall():
        table_name = name[0]
        print(f"\n### Tablo: {table_name} ###")

        # Her bir tablonun sütun bilgilerini al
        res2 = cur.execute(f"PRAGMA table_info('{table_name}');")
        for col in res2.fetchall():
            # (sütun_id, sütun_adı, veri_tipi, not_null, default_deger, primary_key)
            print(f"  - Sütun: {col[1]}, Tip: {col[2]}, Gerekli Mi?: {'Evet' if col[3] else 'Hayır'}")

except sqlite3.Error as e:
    print(f"Bir veritabanı hatası oluştu: {e}")
finally:
    # Bağlantıyı kapat
    if con:
        con.close()