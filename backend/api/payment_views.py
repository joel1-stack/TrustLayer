import json
import uuid
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Transaction, Wallet, MpesaPayment
from .serializers import TransactionSerializer
from .mpesa import MpesaClient
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


class CsrfExemptSessionAuth(SessionAuthentication):
    """Session auth that does not enforce CSRF (for API key fallback)."""
    def enforce_csrf(self, request):
        return  # skip CSRF check


class PaymentViewSet(viewsets.ViewSet):
    """Handle M-PESA STK Push payments"""
    # Use CSRF-exempt session auth so API-key callers aren't blocked
    authentication_classes = [CsrfExemptSessionAuth]
    # AllowAny at the class level; stk_push checks auth itself
    permission_classes = [AllowAny]

    def list(self, request):
        """API root entry for payments."""
        return Response({
            'stk_push': request.build_absolute_uri('stk_push/'),
            'check_status': request.build_absolute_uri('check_status/'),
        })

    @action(detail=False, methods=['post'])
    def stk_push(self, request):
        """Initiate STK Push payment"""
        # --- authenticate via API key OR session ---
        api_key = request.headers.get('X-Api-Key', '')
        user = None
        if api_key and api_key == getattr(settings, 'MPESA_API_KEY', ''):
            user, _ = User.objects.get_or_create(
                username='mpesa_service',
                defaults={'email': 'mpesa@service.local'},
            )
        elif request.user and request.user.is_authenticated:
            user = request.user

        if user is None:
            return Response(
                {'error': 'Authentication required. Provide X-Api-Key header or log in.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            phone_number = request.data.get('phone_number')
            amount = request.data.get('amount')
            description = request.data.get('description', 'TrustLayer Payment')

            if not phone_number or not amount:
                return Response(
                    {'error': 'phone_number and amount are required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            phone_number = self._format_phone(phone_number)

            try:
                amount = float(amount)
                if amount < 1:
                    return Response(
                        {'error': 'Amount must be at least 1 KES'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid amount'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                # Generate a unique reference for the Transaction
                reference = f"TXN-{uuid.uuid4().hex[:12].upper()}"

                txn = Transaction.objects.create(
                    user=user,
                    amount=amount,
                    currency='KES',
                    status='pending',
                    reference=reference,
                    description=description,
                )

                mpesa_payment = MpesaPayment.objects.create(
                    transaction=txn,
                    phone_number=phone_number,
                    status='pending',
                )

                # Initiate STK Push via Daraja
                mpesa = MpesaClient()
                stk_response = mpesa.stk_push(
                    phone_number=phone_number,
                    amount=amount,
                    account_reference=reference,
                    transaction_desc=description,
                )

                if 'error' in stk_response:
                    mpesa_payment.status = 'failed'
                    mpesa_payment.result_desc = stk_response.get('error')
                    mpesa_payment.save()
                    txn.status = 'failed'
                    txn.save()
                    return Response(
                        {'error': 'Failed to initiate payment', 'details': stk_response},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                # STK Push accepted
                mpesa_payment.checkout_request_id = stk_response.get('CheckoutRequestID')
                mpesa_payment.merchant_request_id = stk_response.get('MerchantRequestID')
                mpesa_payment.status = 'processing'
                mpesa_payment.save()

                return Response({
                    'success': True,
                    'message': 'STK Push initiated. Check your phone.',
                    'transaction_id': txn.id,
                    'checkout_request_id': mpesa_payment.checkout_request_id,
                    'amount': amount,
                    'phone_number': phone_number,
                })

        except Exception as e:
            logger.error(f"Error in STK Push: {e}", exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def check_status(self, request):
        """Check status of M-PESA payment"""
        checkout_request_id = request.query_params.get('checkout_request_id')

        if not checkout_request_id:
            return Response(
                {'error': 'checkout_request_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mpesa_payment = MpesaPayment.objects.get(
                checkout_request_id=checkout_request_id,
            )
            return Response({
                'transaction_id': mpesa_payment.transaction.id,
                'status': mpesa_payment.status,
                'mpesa_receipt': mpesa_payment.mpesa_receipt_number,
                'result_description': mpesa_payment.result_desc,
                'created_at': mpesa_payment.created_at,
                'updated_at': mpesa_payment.updated_at,
            })
        except MpesaPayment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @staticmethod
    def _format_phone(phone):
        """Ensure phone number is in 254XXXXXXXXX format"""
        phone = str(phone).strip()
        phone = ''.join(filter(str.isdigit, phone))
        if phone.startswith('07') or phone.startswith('01'):
            phone = '254' + phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        elif phone.startswith('0'):
            phone = '254' + phone[1:]
        return phone


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """M-PESA callback endpoint"""
    try:
        data = json.loads(request.body)
        logger.info(f"M-PESA Callback received: {data}")

        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})

        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        if not checkout_request_id:
            logger.error("Callback missing CheckoutRequestID")
            return Response({'status': 'error', 'detail': 'Missing CheckoutRequestID'}, status=400)

        try:
            mpesa_payment = MpesaPayment.objects.get(checkout_request_id=checkout_request_id)
        except MpesaPayment.DoesNotExist:
            logger.error(f"Payment not found: {checkout_request_id}")
            return Response({'status': 'ok'})

        if result_code == 0:
            # Successful payment
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])

            mpesa_receipt = None
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt = item.get('Value')
                    break

            with transaction.atomic():
                mpesa_payment.status = 'completed'
                mpesa_payment.mpesa_receipt_number = mpesa_receipt
                mpesa_payment.result_code = result_code
                mpesa_payment.result_desc = result_desc
                mpesa_payment.save()

                txn = mpesa_payment.transaction
                txn.status = 'completed'
                if mpesa_receipt:
                    txn.reference = mpesa_receipt
                txn.save()

                wallet, _ = Wallet.objects.get_or_create(
                    user=txn.user,
                    defaults={'currency': 'KES'},
                )
                wallet.balance += txn.amount
                wallet.save()

                logger.info(f"Payment completed: {mpesa_receipt}")
        else:
            # Failed payment
            mpesa_payment.status = 'failed'
            mpesa_payment.result_code = result_code
            mpesa_payment.result_desc = result_desc
            mpesa_payment.save()

            mpesa_payment.transaction.status = 'failed'
            mpesa_payment.transaction.save()

            logger.warning(f"Payment failed: {result_desc}")

        return Response({'status': 'ok'})

    except json.JSONDecodeError:
        logger.error("Invalid JSON in callback")
        return Response({'status': 'error'}, status=400)
    except Exception as e:
        logger.error(f"Error processing callback: {e}", exc_info=True)
        return Response({'status': 'error'}, status=500)
