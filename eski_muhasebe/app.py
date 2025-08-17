# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import json

app = Flask(__name__)
app.secret_key = 'guvenli-bir-anahtar'  # Oturum için gerekli

DB_PATH = 'ruya_eczane.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- GİRİŞ SAYFASI ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kullanici = request.form['kullanici']
        sifre = request.form['sifre']
        if kullanici == 'admin' and sifre == '1234':
            session['logged_in'] = True
            return redirect(url_for('anasayfa'))
        else:
            return render_template('login.html', hata='Hatalı kullanıcı adı veya şifre!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- ANASAYFA ---
@app.route('/', methods=['GET', 'POST'])
def anasayfa():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    gelir_query = "SELECT SUM(genel_toplam) as toplam FROM KurumsalSatislar"
    gider_query = "SELECT SUM(toplam_tutar) as toplam FROM Giderler"
    kasa_query = "SELECT tarih, nakit_tutar, kart_tutar, toplam_tutar FROM GunlukKasa"

    if start_date and end_date:
        gelir_query += f" WHERE tarih BETWEEN '{start_date}' AND '{end_date}'"
        gider_query += f" WHERE tarih BETWEEN '{start_date}' AND '{end_date}'"
        kasa_query += f" WHERE tarih BETWEEN '{start_date}' AND '{end_date}'"

    kasa_query += " ORDER BY tarih DESC LIMIT 7"

    gelir = conn.execute(gelir_query).fetchone()['toplam'] or 0
    gider = conn.execute(gider_query).fetchone()['toplam'] or 0
    net = gelir - gider
    kasa_listesi = conn.execute(kasa_query).fetchall()
    conn.close()

    # Grafik verileri için JSON oluştur
    grafik_data = {
        "labels": [k['tarih'] for k in kasa_listesi][::-1],
        "nakit": [k['nakit_tutar'] for k in kasa_listesi][::-1],
        "kart": [k['kart_tutar'] for k in kasa_listesi][::-1],
        "toplam": [k['toplam_tutar'] for k in kasa_listesi][::-1]
    }

    tablolar = [
        'Cariler',
        'Giderler',
        'CekSenetler',
        'KurumsalSatislar',
        'KrediKartiHarcamalari',
        'KrediKartiOdemeleri',
        'GunlukKasa',
        'Z_Raporlari',
        'BankaKredileri',
        'KrediTaksitleri',
        'KasaHesaplamalari',
        'Faturalar',
        'Odemeler'
    ]

    return render_template(
        'dashboard.html',
        gelir=gelir,
        gider=gider,
        net=net,
        kasa_listesi=kasa_listesi,
        tablolar=tablolar,
        start_date=start_date,
        end_date=end_date,
        grafik_data=json.dumps(grafik_data)
    )

# --- TABLO GÖRÜNTÜLEME SAYFALARI ---
@app.route('/tablo/<tablo_adi>')
def tablo_goster(tablo_adi):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        veri = conn.execute(f"SELECT * FROM {tablo_adi} ORDER BY ROWID DESC LIMIT 50").fetchall()
        kolonlar = [kol[0] for kol in conn.execute(f"PRAGMA table_info({tablo_adi})").fetchall()]
    except Exception as e:
        return f"Hata: {e}"
    finally:
        conn.close()

    return render_template('tablo.html', tablo_adi=tablo_adi, kolonlar=kolonlar, veri=veri)
@app.route('/soru-cevap', methods=['GET', 'POST'])
def soru_cevap():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cevap = None
    if request.method == 'POST':
        soru = request.form['soru'].lower()

        conn = get_db_connection()

        try:
            if "en çok harcama" in soru:
                row = conn.execute("SELECT aciklama, toplam_tutar FROM Giderler ORDER BY toplam_tutar DESC LIMIT 1").fetchone()
                if row:
                    cevap = f"En çok harcama: {row['aciklama']} ({row['toplam_tutar']} TL)"
                else:
                    cevap = "Gider verisi bulunamadı."

            elif "bugün kasa" in soru:
                from datetime import datetime
                bugun = datetime.today().strftime('%Y-%m-%d')
                row = conn.execute("SELECT * FROM GunlukKasa WHERE tarih = ?", (bugun,)).fetchone()
                if row:
                    cevap = f"Bugünkü kasa: Nakit {row['nakit_tutar']} TL, Kart {row['kart_tutar']} TL, Toplam {row['toplam_tutar']} TL"
                else:
                    cevap = "Bugün için kasa verisi bulunamadı."

            elif "kartla ödeme oranı" in soru or "kart oranı" in soru:
                rows = conn.execute("SELECT kart_tutar, toplam_tutar FROM GunlukKasa ORDER BY tarih DESC LIMIT 7").fetchall()
                kart_toplam = sum(r['kart_tutar'] for r in rows)
                genel_toplam = sum(r['toplam_tutar'] for r in rows)
                oran = (kart_toplam / genel_toplam) * 100 if genel_toplam else 0
                cevap = f"Son 7 günde kartla ödeme oranı: %{oran:.1f}"

            else:
                cevap = "Bu soruya henüz cevap veremiyorum."
        except Exception as e:
            cevap = f"Hata oluştu: {str(e)}"
        finally:
            conn.close()

    return render_template('soru_cevap.html', cevap=cevap)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# --- dashboard.html (templates klasörüne kaydet) güncellenecek alanlar: ---
"""
<form method="post" style="margin-bottom:20px;">
    <label>Başlangıç Tarihi:</label>
    <input type="date" name="start_date" value="{{ start_date }}">
    <label>Bitiş Tarihi:</label>
    <input type="date" name="end_date" value="{{ end_date }}">
    <button type="submit">Filtrele</button>
</form>

<!-- Grafik kutusu -->
<div class="kutu">
    <h2>📊 Kasa Hareketleri Grafiği</h2>
    <canvas id="kasaChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    const data = {{ grafik_data | safe }};
    const ctx = document.getElementById('kasaChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Nakit',
                    data: data.nakit,
                    borderColor: 'green',
                    fill: false
                },
                {
                    label: 'Kart',
                    data: data.kart,
                    borderColor: 'blue',
                    fill: false
                },
                {
                    label: 'Toplam',
                    data: data.toplam,
                    borderColor: 'black',
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
</script>
"""

