from django.apps import AppConfig

class SavingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'savings'

    def ready(self):
        # Start the monthly interest scheduler when Django starts
        from .tasks import schedule_monthly_interest
        schedule_monthly_interest()
