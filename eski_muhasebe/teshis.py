# teshis.py (v2 - Daha Detaylı DUMP Metodu ile)
from zeep import Client
import ayarlar_yonetimi
from zeep.transports import Transport
import requests

# Ayarları yükle
ayarlar = ayarlar_yonetimi.ayarlari_yukle()
EFATURA_USERNAME = ayarlar.get("efatura_kullanici_adi", "").strip()
EFATURA_PASSWORD = ayarlar.get("efatura_sifre", "").strip()

WSDL_URL = "https://portal.eczacikartfatura.com/QueryInvoiceService/QueryDocumentWS?wsdl"

print(f"Servise bağlanılıyor: {WSDL_URL}")
print("Mevcut tüm metotlar ve tipler listelenecek...")

try:
    session = requests.Session()
    session.headers.update({
        'Username': EFATURA_USERNAME,
        'Password': EFATURA_PASSWORD,
    })
    transport = Transport(session=session)
    client = Client(wsdl=WSDL_URL, transport=transport)

    # Önceki print(client.service) yerine WSDL'in tamamını döken dump() metodunu kullanıyoruz.
    # Bu bize tüm metotları, parametreleri ve tipleri detaylıca gösterecek.
    print("\n--- SERVİS TANIMI (WSDL DUMP) ---")
    client.wsdl.dump()
    print("--- TANIM SONU ---\n")
    
except Exception as e:
    print(f"Bir hata oluştu: {e}")

input("Kapatmak için Enter'a basın...")