# randevu/signals.py

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import TemsilciProfili

# Bir User objesi kaydedildikten sonra bu fonksiyon çalışacak
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Eğer yeni bir kullanıcı oluşturulmuşsa...
    if created:
        # ...o kullanıcı için boş bir TemsilciProfili oluştur.
        TemsilciProfili.objects.create(user=instance)