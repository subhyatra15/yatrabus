import logging
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError
from django.core.mail import send_mail
from django.conf import settings

from .models import Device

logger = logging.getLogger(__name__)


def send_user_notification(user, title, body, data=None, device_type=None):
    qs = Device.objects.filter(user=user)
    if device_type:
        qs = qs.filter(device=device_type)

    tokens = list(qs.values_list("token", flat=True))
    if not tokens:
        return None

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(priority="high"),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1)
            )
        ),
    )

    try:
        response = messaging.send_each_for_multicast(message)
    except FirebaseError as e:
        logger.exception("FCM send failed for user %s: %s", user.id, e)
        return None

    dead = [
        tokens[i]
        for i, r in enumerate(response.responses)
        if not r.success
        and isinstance(r.exception, messaging.UnregisteredError)
    ]
    if dead:
        Device.objects.filter(token__in=dead).delete()
        logger.info("Removed %d dead tokens for user %s", len(dead), user.id)

    return response


def send_user_email(user, subject, message):
    if not user.email:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Email failed for user %s", user.id)
        return False