from django.core.management.base import BaseCommand
from django.utils import timezone
from randevu.models import Randevu
import datetime

class Command(BaseCommand):
    help = 'Geçmiş tarihli ve boşta kalmış randevuları temizler, durumu güncellenmemiş olanları arşivler.'

    def handle(self, *args, **kwargs):
        now = timezone.now()

        # 1. Adım: Bir günden daha eski ve alınmamış (boş) randevu slotlarını sil.
        one_day_ago = now - datetime.timedelta(days=1)
        deleted_count, _ = Randevu.objects.filter(
            temsilci__isnull=True, 
            tarih_saat__lt=one_day_ago
        ).delete()
        self.stdout.write(self.style.SUCCESS(f'{deleted_count} adet geçmiş tarihli boş randevu silindi.'))

        # 2. Adım: Tarihi geçmiş ve hala "Onaylandı" durumunda olan randevuları "Gelinmedi" olarak işaretle.
        updated_count = Randevu.objects.filter(
            temsilci__isnull=False,
            status='onaylandi',
            tarih_saat__lt=now
        ).update(status='gelinmedi')
        self.stdout.write(self.style.SUCCESS(f'{updated_count} adet randevu "Gelinmedi" olarak güncellendi.'))

        self.stdout.write(self.style.SUCCESS('Otomatik bakım görevi başarıyla tamamlandı.'))