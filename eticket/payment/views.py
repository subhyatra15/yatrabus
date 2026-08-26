import uuid
from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets, views 
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from booking.models import Booking
from .models import Payment, PaymentLog
from .serializers import PaymentSerializer

import hmac
import hashlib
import base64
import requests
import json


from django.conf import settings

from .models import Payment


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        if user.role == "A":
            return Payment.objects.select_related(
                "booking",
                "customer"
            )

        return Payment.objects.select_related(
            "booking",
            "customer"
        ).filter(customer=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        booking = serializer.validated_data["booking"]

        payment = Payment.objects.create(

            booking=booking,

            customer=request.user,

            payment_method=serializer.validated_data["payment_method"],

            gateway=serializer.validated_data.get(
                "gateway"
            ),

            amount=serializer.validated_data["amount"],

            currency=serializer.validated_data.get(
                "currency",
                "NPR"
            ),

            status="PENDING",

            transaction_id=uuid.uuid4().hex.upper(),
        )

        PaymentLog.objects.create(

            payment=payment,

            request_data=request.data,

            response_data={
                "message": "Payment initiated successfully."
            }
        )

        # Cash payment is immediately successful
        if payment.payment_method == "CASH":

            payment.status = "SUCCESS"
            payment.payment_date = timezone.now()
            payment.save()

            booking.booking_status = "PAID"
            booking.save()

        serializer = PaymentSerializer(
            payment,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):

        payment = self.get_object()

        if payment.status == "SUCCESS":

            return Response(
                {
                    "message":
                    "Successful payment cannot be deleted."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.delete()

        return Response(
            {
                "message": "Deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )
    


# Esewa Payment Initiate
class EsewaInitiateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        booking_id = request.data.get("booking_id")

        if not booking_id:
            return Response(
                {"error": "booking_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.get(
                id=booking_id,
                customer=request.user
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if booking.booking_status != "PENDING":
            return Response(
                {"error": "Only pending bookings can be paid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction_uuid = str(uuid.uuid4())
        amount = str(booking.total_amount)
        tax_amount = "0"
        product_service_charge = "0"
        product_delivery_charge = "0"
        total_amount = amount

        signed_field_names = "total_amount,transaction_uuid,product_code"

        message = (
            f"total_amount={total_amount},"
            f"transaction_uuid={transaction_uuid},"
            f"product_code={settings.ESEWA_PRODUCT_CODE}"
        )

        signature = base64.b64encode(
            hmac.new(
                settings.ESEWA_SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
        ).decode()

        payment, created = Payment.objects.update_or_create(
            booking=booking,
            payment_method="ESEWA",
            defaults={
                "customer": request.user,
                "amount": booking.total_amount,
                "transaction_id": transaction_uuid,
                "status": "PENDING",
                "gateway": "ESEWA",
            }
        )

        return Response(
            {
                "payment_url": settings.ESEWA_PAYMENT_URL,
                "amount": amount,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "transaction_uuid": transaction_uuid,
                "product_code": settings.ESEWA_PRODUCT_CODE,
                "product_service_charge": product_service_charge,
                "product_delivery_charge": product_delivery_charge,
                "success_url": settings.ESEWA_SUCCESS_URL,
                "failure_url": settings.ESEWA_FAILURE_URL,
                "signed_field_names": signed_field_names,
                "signature": signature,
            },
            status=status.HTTP_200_OK
        )
    

# Esewa Payment Verfiy
class EsewaVerifyView(views.APIView):
    def post(self, request):
        transaction_uuid = request.data.get("transaction_uuid")

        if not transaction_uuid:
            return Response(
                {"message": "Transaction UUID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_obj = Payment.objects.filter(
            transaction_id=transaction_uuid
        ).first()

        if not payment_obj:
            return Response(
                {"message": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        payment_obj.status = "SUCCESS"
        payment_obj.save()

        booking = payment_obj.booking
        booking.booking_status = "PAID"
        booking.save()

        return Response(
            {
                "message": "Payment verified successfully"
            },
            status=status.HTTP_200_OK
        )


# Khalti Initiate View
class KhaltiInitiateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response(
                {
                    'message':'Booking Id is required',
                    'status' : status.HTTP_400_BAD_REQUEST
                }
            )
        
        try:
            booking = Booking.objects.get(
                id=booking_id,
                customer=request.user
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if booking.booking_status != "PENDING":
            return Response(
                {"error": "Only pending bookings can be paid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment, created = Payment.objects.update_or_create(
            booking=booking,
            payment_method="KHALTI",
            defaults={
                "customer": request.user,
                "amount": booking.total_amount,
                "status": "PENDING",
                "gateway": "KHALTI",
            }
        )
        
        url = settings.KHALTI_INITIATE_URL

        payload = json.dumps({
            "return_url": settings.RETURN_URL,
            "website_url": settings.WEBSITE_URL,
            "amount": int(payment.amount * 100),
            "purchase_order_id": booking.booking_number,
            "purchase_order_name": "Bus Ticket",
            "customer_info": {
            "name": request.user.fullName,
            "email": request.user.email,
            "phone": request.user.phone
            }
        })
        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.json()

        print(response.status_code)
        print(response.text)

        if response.status_code != 200:
            return Response(
                {
                    "message": "Khalti initiation failed",
                    "error": data
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.transaction_id = data.get("pidx")
        payment.save()

        return Response(
            {
                "message": "Successfully Initiated Khalti",
                "payment_url": data.get("payment_url"),
                "pidx": data.get("pidx")
            },
            status=status.HTTP_201_CREATED
        )


# Khalti Payment Verfiy
class KhaltiVerifyView(views.APIView):
    def post(self, request):
        transaction_uuid = request.data.get("transaction_uuid")

        if not transaction_uuid:
            return Response(
                {"message": "Transaction UUID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_obj = Payment.objects.filter(
            transaction_id=transaction_uuid
        ).first()

        if not payment_obj:
            return Response(
                {"message": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        payment_obj.status = "SUCCESS"
        payment_obj.save()

        booking = payment_obj.booking
        booking.booking_status = "PAID"
        booking.save()

        return Response(
            {
                "message": "Payment verified successfully"
            },
            status=status.HTTP_200_OK
        )