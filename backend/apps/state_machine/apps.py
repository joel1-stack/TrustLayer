from django.apps import AppConfig

class StateMachineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.state_machine'
    verbose_name = 'State Machine Engine'