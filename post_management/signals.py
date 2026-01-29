from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import NewsPost
from .api.utils import send_news_notification
import threading

@receiver(post_save, sender=NewsPost)
def trigger_notification_on_new_post(sender, instance, created, **kwargs):
    """
    Triggers a Firebase notification when a new NewsPost is created and active.
    """
    print(f"DEBUG: Signal received for Post {instance.id}. Created: {created}, Status: {instance.status}, IsActive: {instance.is_active}")
    
    if created and instance.status == 'active' and instance.is_active:
        print("DEBUG: Conditions met. Queuing notification...")
        
        def send_notification_task():
            print(f"DEBUG: Executing notification task for {instance.id}")
            send_news_notification(instance.id)

        # Ensure DB transaction is committed before starting thread
        transaction.on_commit(send_notification_task)
    else:
        print("DEBUG: Conditions NOT met.")
