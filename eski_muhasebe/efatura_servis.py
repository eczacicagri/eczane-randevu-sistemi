# efatura_servis.py (Doğrudan PDF İsteyen Final Sürüm)

from zeep import Client
from zeep.transports import Transport
import requests
import ayarlar_yonetimi
import os
import base64

# Ayarları yükle
ayarlar = ayarlar_yonetimi.ayarlari_yukle()
EFATURA_USERNAME = ayarlar.get("efatura_kullanici_adi", "").strip()
EFATURA_PASSWORD = ayarlar.get("efatura_sifre", "").strip()

# Servis adresleri
QUERY_WSDL = "https://portal.eczacikartfatura.com/QueryInvoiceService/QueryDocumentWS?wsdl"

def _get_zeep_client(wsdl_url=QUERY_WSDL):
    """Zeep client'ı oluşturur."""
    if not EFATURA_USERNAME or not EFATURA_PASSWORD:
        raise ValueError("Hata: E-Fatura kullanıcı bilgileri Ayarlar menüsünden girilmemiş.")
    
    session = requests.Session()
    session.headers.update({
        'Username': EFATURA_USERNAME,
        'Password': EFATURA_PASSWORD,
    })
    transport = Transport(session=session)
    client = Client(wsdl=wsdl_url, transport=transport)
    return client

def get_inbox_documents(start_date, end_date):
    """Gelen e-faturaları sorgular."""
    client = _get_zeep_client()
    bas_tarih_str = start_date.strftime('%Y-%m-%d')
    bit_tarih_str = end_date.strftime('%Y-%m-%d')
    return client.service.QueryInboxDocumentsWithDocumentDate(
        startDate=bas_tarih_str, endDate=bit_tarih_str, documentType='1',
        queried='ALL', withXML='NONE', takenFromEntegrator='ALL', minRecordId='0'
    )

def get_outbox_documents(start_date, end_date):
    """Giden e-faturaları sorgular."""
    client = _get_zeep_client()
    bas_tarih_str = start_date.strftime('%Y-%m-%d')
    bit_tarih_str = end_date.strftime('%Y-%m-%d')
    return client.service.QueryOutboxDocumentsWithDocumentDate(
        startDate=bas_tarih_str, endDate=bit_tarih_str, documentType='1',
        queried='ALL', withXML='NONE', minRecordId='0'
    )

def download_and_process_invoice(document_uuid, download_path, invoice_type='inbox'):
    """Faturanın PDF içeriğini doğrudan sunucudan ister ve dosyaya kaydeder."""
    try:
        query_client = _get_zeep_client()
        
        print(f"Faturanın PDF içeriği sunucudan isteniyor: {document_uuid}")
        
        param_type = 'Document_UUID'
        # DOKÜMANDA BELİRTİLEN 'PDF' SEÇENEĞİNİ KULLANIYORUZ
        content_type_to_request = 'PDF' 

        if invoice_type == 'inbox':
            response = query_client.service.QueryInboxDocument(
                paramType=param_type, 
                parameter=document_uuid, 
                withXML=content_type_to_request
            )
        else: # outbox
            response = query_client.service.QueryOutboxDocument(
                paramType=param_type, 
                parameter=document_uuid, 
                withXML=content_type_to_request
            )

        if response and response.documents:
            document = response.documents[0]
            # Dokümanda belirtilen 'content' alanını kullanıyoruz.
            content_base64 = getattr(document, 'content', getattr(document, 'document_content', None))
            
            if content_base64:
                # Dosyayı .pdf uzantısıyla kaydediyoruz
                pdf_file_path = os.path.join(download_path, 'fatura_gorunumu.pdf')
                with open(pdf_file_path, 'wb') as f:
                    # Gelen veri Base64 formatında olduğu için decode ediyoruz
                    f.write(base64.b64decode(content_base64))
                print("PDF başarıyla oluşturuldu.")
                return True, pdf_file_path
            else:
                return False, "Sunucu başarılı yanıt verdi ancak fatura içeriği (PDF) boş geldi."
        else:
            state_exp = getattr(response, 'stateExplanation', 'Bilinmeyen bir hata oluştu.')
            return False, f"Sunucudan fatura alınamadı. Sunucu yanıtı: {state_exp}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Fatura işlenirken bir hata oluştu: {e}"