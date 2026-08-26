from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PaymentViewSet,
    EsewaInitiateView,
    EsewaVerifyView,
    KhaltiInitiateView,
    KhaltiVerifyView,
    # StripePaymentIntentView,
    # StripeWebhookView,
    # RefundView,
)

router = DefaultRouter()

router.register(
    r"payments",
    PaymentViewSet,
    basename="payment"
)

urlpatterns = [
    path("", include(router.urls)),

    # eSewa
    path(
        "payments/esewa/initiate/",
        EsewaInitiateView.as_view(),
        name="esewa-initiate",
    ),
    path(
        "payments/esewa/verify/",
        EsewaVerifyView.as_view(),
        name="esewa-verify",
    ),

    # Khalti
    path(
        "payments/khalti/initiate/",
        KhaltiInitiateView.as_view(),
        name="khalti-initiate",
    ),
    path(
        "payments/khalti/verify/",
        KhaltiVerifyView.as_view(),
        name="khalti-verify",
    ),

    # # Stripe
    # path(
    #     "payments/stripe/create-intent/",
    #     StripePaymentIntentView.as_view(),
    #     name="stripe-create-intent",
    # ),
    # path(
    #     "payments/stripe/webhook/",
    #     StripeWebhookView.as_view(),
    #     name="stripe-webhook",
    # ),

    # # Refund
    # path(
    #     "payments/refund/",
    #     RefundView.as_view(),
    #     name="payment-refund",
    # ),
]