import sqlite3
from django.core.management.base import BaseCommand
from django.conf import settings
from muhasebe.models import Cari, Fatura, Odeme
from datetime import datetime

OLD_DB_PATH = settings.BASE_DIR.parent / 'eski_muhasebe/ruya_eczane.db'

class Command(BaseCommand):
    help = 'Eski SQLite veritabanından muhasebe verilerini (Cari, Fatura, Odeme) aktarır.'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write(f"Eski veritabanı okunuyor: {OLD_DB_PATH}")
            con = sqlite3.connect(OLD_DB_PATH)
            cur = con.cursor()

            # Önce Cariler'i aktarıyoruz ki faturaları ve ödemeleri onlara bağlayabilelim.
            self.cari_id_map = self.import_cariler(cur)
            self.import_faturalar(cur)
            self.import_odemeler(cur)

            con.close()
            self.stdout.write(self.style.SUCCESS('Veri aktarımı başarıyla tamamlandı.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"HATA: Eski veritabanı dosyası bulunamadı: {OLD_DB_PATH}"))

    def import_cariler(self, cur):
        self.stdout.write("Cariler aktarılıyor...")
        # Eski ID'leri yeni Django objeleriyle eşleştirmek için bir harita oluşturuyoruz.
        cari_id_map = {}
        # Sorguya 'cari_id'yi de ekledik.
        cur.execute("SELECT cari_id, unvan, vergi_no, adres, telefon, tip FROM Cariler")
        for row in cur.fetchall():
            old_id = row[0]
            cari, created = Cari.objects.update_or_create(
                unvan=row[1],
                defaults={
                    'vergi_no': row[2], 'adres': row[3], 'telefon': row[4],
                    'tip': row[5]
                }
            )
            cari_id_map[old_id] = cari # Eski ID'yi yeni objeye bağlıyoruz.
            if created:
                self.stdout.write(f"  - {cari.unvan} oluşturuldu.")
        return cari_id_map

    def import_faturalar(self, cur):
        self.stdout.write("Faturalar aktarılıyor...")
        cur.execute("SELECT fatura_no, cari_id, tarih, tip, ara_toplam, kdv_toplam, genel_toplam, odeme_durumu, efatura_uuid, efatura_durum FROM Faturalar")
        for row in cur.fetchall():
            # Eski cari_id'yi kullanarak yeni Cari objesini haritadan buluyoruz.
            cari_obj = self.cari_id_map.get(row[1])
            if not cari_obj:
                continue # Eşleşen cari bulunamazsa bu faturayı atla
            
            # Tarih formatını Django'nun anlayacağı şekle çeviriyoruz.
            try:
                tarih_obj = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                tarih_obj = datetime.strptime(row[2], '%Y-%m-%d').date()

            Fatura.objects.update_or_create(
                fatura_no=row[0],
                cari=cari_obj,
                defaults={
                    'tarih': tarih_obj, 'tip': row[3], 'ara_toplam': row[4], 'kdv_toplam': row[5],
                    'genel_toplam': row[6], 'odeme_durumu': row[7], 'efatura_uuid': row[8], 'efatura_durum': row[9]
                }
            )
    
    def import_odemeler(self, cur):
        self.stdout.write("Ödemeler aktarılıyor...")
        cur.execute("SELECT cari_id, tarih, tutar, islem_tipi, odeme_yontemi, aciklama FROM Odemeler")
        for row in cur.fetchall():
            cari_obj = self.cari_id_map.get(row[0])
            if not cari_obj:
                continue

            try:
                tarih_obj = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                tarih_obj = datetime.strptime(row[1], '%Y-%m-%d').date()

            Odeme.objects.create(
                cari=cari_obj, tarih=tarih_obj, tutar=row[2], islem_tipi=row[3],
                odeme_yontemi=row[4], aciklama=row[5]
            )