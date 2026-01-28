import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from post_management.models import NewsPost
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """Validates and initializes the Firebase Admin app."""
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin App initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False
    return True

def send_topic_notification(title, body, image_url=None, data=None, topic='news'):
    """
    Generic function to send notification to a topic.
    """
    if not initialize_firebase():
        return {"status": "error", "message": "Firebase not initialized"}

    if data is None:
        data = {}

    # Ensure all data values are strings
    data = {k: str(v) for k, v in data.items()}

    try:
        message = messaging.Message(
            topic=topic,
            notification=messaging.Notification(
                title=title,
                body=body,
                image=image_url if image_url else None,
            ),
            data=data,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    image=image_url if image_url else None,
                    channel_id='default', 
                    default_sound=True,
                    default_vibrate_timings=True,
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        mutable_content=True,
                        sound="default"
                    )
                ),
                fcm_options=messaging.APNSFCMOptions(
                    image=image_url if image_url else None
                )
            )
        )

        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return {"status": "success", "message_id": response}

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return {"status": "error", "message": str(e)}

def send_news_notification(news_id):
    """
    Wrapper for sending NewsPost notifications.
    """
    try:
        news_obj = NewsPost.objects.get(id=news_id)
    except NewsPost.DoesNotExist:
        return {"status": "error", "message": "NewsPost not found"}

    title = news_obj.post_title if news_obj.post_title else "New News Alert"
    body = news_obj.post_short_des if news_obj.post_short_des else "Check out the latest news!"
    
    image_url = ""
    if news_obj.post_image:
        try:
            image_url = news_obj.post_image.url 
            if image_url.startswith('/'):
                 image_url = f"https://janhimachal.com{image_url}"
        except:
            pass

    data = {
        "id": str(news_obj.id),
        "type": "news",
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
    }

    return send_topic_notification(title, body, image_url, data, topic='news')


def send_custom_notification(custom_notif_obj):
    """
    Wrapper for sending Custom Notifications.
    """
    title = custom_notif_obj.title
    body = custom_notif_obj.message
    
    image_url = ""
    if custom_notif_obj.image:
        try:
            image_url = custom_notif_obj.image.url
            if image_url.startswith('/'):
                image_url = f"https://janhimachal.com{image_url}"
        except:
            pass
            
    data = {
        "type": "custom",
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
    }
    
    # DEBUG LOG
    print(f"DEBUG: Sending Custom Notification. Title: {title}, Body: {body}, Image URL: {image_url}")

    return send_topic_notification(title, body, image_url, data, topic='news')
