from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.timezone import now  # Import now from timezone

class SecondConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'second'

    def ready(self):
        # Import models here to avoid AppRegistryNotReady exception
        from .models import CartItem
        # Register signals when the app is ready
        post_save.connect(update_item_interaction, sender=CartItem)

def update_item_interaction(sender, instance, **kwargs):
    """
    Signal receiver to update last_interacted timestamp when CartItem is saved.
    """
    # Only update if this isn't a raw save (e.g., during fixtures loading)
    if not kwargs.get('raw', False):
        instance.item.last_interacted = now()
        instance.item.save(update_fields=['last_interacted'])  # Only update this field*