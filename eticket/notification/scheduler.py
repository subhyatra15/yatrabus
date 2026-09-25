from datetime import timedelta

from django.utils import timezone

from .tasks import send_booking_reminder


def schedule_booking_reminder(
    booking,
    booking_type,
    route,
    departure_time,
):

    reminder_time = departure_time - timedelta(minutes=30)
    if reminder_time <= timezone.now():
        return None

    task = send_booking_reminder.apply_async(
        args=[
            booking.user.id,
            booking_type,
            booking.id,
            route,
            departure_time.strftime("%Y-%m-%d %H:%M"),
        ],
        eta=reminder_time,
    )

    return task.id