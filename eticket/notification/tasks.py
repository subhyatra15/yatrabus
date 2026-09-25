from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .services import (
    send_user_notification,
    send_user_email,
)

@shared_task
def send_departure_reminders():

    from booking.models import Booking
    from hiace.models import HiaceBooking

    now = timezone.now()

    reminder_start = now + timedelta(minutes=29)
    reminder_end = now + timedelta(minutes=31)

    # ==========================================
    # BUS
    # ==========================================

    bus_bookings = Booking.objects.select_related(
        "customer",
        "schedule",
    ).filter(
        booking_status="PAID",
        departure_reminder_sent=False,
        schedule__departure_time__gte=reminder_start,
        schedule__departure_time__lt=reminder_end,
    )

    for booking in bus_bookings:

        departure_time = booking.schedule.departure_time

        # ------------------------------------------
        # PUSH NOTIFICATION
        # ------------------------------------------

        send_user_notification(
            user=booking.customer,
            title="Bus Departure Reminder",
            body=(
                f"Your bus departs in 30 minutes. "
                f"Booking: {booking.booking_number}. "
                f"Departure: "
                f"{departure_time.strftime('%I:%M %p')}"
            ),
            data={
                "type": "DEPARTURE_REMINDER",
                "booking_type": "BUS",
                "booking_id": booking.id,
                "booking_number": booking.booking_number,
            },
        )

        # ------------------------------------------
        # EMAIL
        # ------------------------------------------

        send_user_email(
            user=booking.customer,
            subject=(
                f"Bus Departure Reminder - "
                f"{booking.booking_number}"
            ),
            message=(
                f"Dear {booking.customer.get_full_name() or booking.customer.username},\n\n"
                f"This is a reminder that your bus will "
                f"depart in 30 minutes.\n\n"
                f"Booking Number: {booking.booking_number}\n"
                f"Departure Time: "
                f"{departure_time.strftime('%I:%M %p')}\n\n"
                f"Please arrive at the boarding point on time.\n\n"
                f"Thank you for using YatraBus."
            ),
        )

        booking.departure_reminder_sent = True

        booking.save(
            update_fields=["departure_reminder_sent"]
        )

    # ==========================================
    # HIACE
    # ==========================================

    hiace_bookings = HiaceBooking.objects.select_related(
        "customer",
        "schedule",
    ).filter(
        booking_status="PAID",
        departure_reminder_sent=False,
        schedule__departure_time__gte=reminder_start,
        schedule__departure_time__lt=reminder_end,
    )

    for booking in hiace_bookings:

        departure_time = booking.schedule.departure_time

        # ------------------------------------------
        # PUSH NOTIFICATION
        # ------------------------------------------

        send_user_notification(
            user=booking.customer,
            title="Hiace Departure Reminder",
            body=(
                f"Your Hiace departs in 30 minutes. "
                f"Booking: {booking.booking_number}. "
                f"Departure: "
                f"{departure_time.strftime('%I:%M %p')}"
            ),
            data={
                "type": "DEPARTURE_REMINDER",
                "booking_type": "HIACE",
                "booking_id": booking.id,
                "booking_number": booking.booking_number,
            },
        )

        # ------------------------------------------
        # EMAIL
        # ------------------------------------------

        send_user_email(
            user=booking.customer,
            subject=(
                f"Hiace Departure Reminder - "
                f"{booking.booking_number}"
            ),
            message=(
                f"Dear {booking.customer.get_full_name() or booking.customer.username},\n\n"
                f"This is a reminder that your Hiace will "
                f"depart in 30 minutes.\n\n"
                f"Booking Number: {booking.booking_number}\n"
                f"Departure Time: "
                f"{departure_time.strftime('%I:%M %p')}\n\n"
                f"Please arrive at the boarding point on time.\n\n"
                f"Thank you for using YatraBus."
            ),
        )

        booking.departure_reminder_sent = True

        booking.save(
            update_fields=["departure_reminder_sent"]
        )

    return {
        "bus": bus_bookings.count(),
        "hiace": hiace_bookings.count(),
    }