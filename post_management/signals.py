from django.db.models.signals import post_save
from django.dispatch import receiver
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
        print("DEBUG: Conditions met. Sending notification...")
        # Run in a separate thread to avoid blocking the save process
        # or causing issues if Firebase takes time.
        # Note: In production with heavy load, use Celery instead of threading.
        process = threading.Thread(target=send_news_notification, args=(instance.id,))
        process.start()
    else:
        print("DEBUG: Conditions NOT met.")
