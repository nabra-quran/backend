from django.apps import AppConfig

class CorrectionappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'correctionApp'
    def ready(self):
        import correctionApp.signals
