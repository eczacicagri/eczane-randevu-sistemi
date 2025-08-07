from django.apps import AppConfig


class RandevuConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'randevu'
    def ready(self):
        import randevu.signals