"""
Escrow Permissions — Who can release, refund, or dispute funds.
"""
import hashlib
from apps.merchants.models import Merchant


class DealAccessPermission:

    @staticmethod
    def is_merchant_owner(request, deal) -> bool:
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth.startswith('Bearer '):
            return False
        key_hash = hashlib.sha256(auth.split(' ')[1].encode()).hexdigest()
        try:
            merchant = Merchant.objects.get(api_key_hash=key_hash, is_active=True)
            return str(deal.merchant_id) == str(merchant.id)
        except Merchant.DoesNotExist:
            return False

    @staticmethod
    def is_buyer(request, deal) -> bool:
        phone = (request.GET.get('phone') or request.POST.get('phone') or '').strip().replace(' ', '')
        if not phone:
            return False
        deal_phone = deal.buyer_phone.strip().replace(' ', '')
        if phone.startswith('0'):    phone      = '254' + phone[1:]
        if deal_phone.startswith('0'): deal_phone = '254' + deal_phone[1:]
        return phone == deal_phone

    @staticmethod
    def is_admin(request) -> bool:
        from django.conf import settings
        token    = request.META.get('HTTP_X_ADMIN_TOKEN', '')
        expected = getattr(settings, 'TRUSTLAYER_ADMIN_TOKEN', '')
        return bool(token and token == expected)
