from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_release_held_deals():
    """
    Runs every 15 minutes via Celery Beat.
    Releases any HELD deal whose auto_release_at has passed (48h window).
    Triggers B2C transfer to the merchant's phone.
    """
    from apps.escrow.models import EscrowDeal
    from apps.escrow.services import EscrowService
    from apps.notifications.services import NotificationService

    overdue = EscrowDeal.objects.filter(
        status='HELD',
        auto_release_at__lte=timezone.now(),
    )

    for deal in overdue:
        deal.status      = 'RELEASED'
        deal.released_at = timezone.now()
        deal.save(update_fields=['status', 'released_at'])

        # Trigger B2C fund release to merchant's phone
        try:
            release = EscrowService.release_funds(deal.deal_code)
            if release.get('success'):
                logger.info(f"Auto-release B2C initiated for {deal.deal_code}")
            else:
                logger.error(f"Auto-release B2C failed for {deal.deal_code}: {release.get('error')}")
        except Exception as e:
            logger.error(f"Auto-release B2C error for {deal.deal_code}: {e}")

        try:
            NotificationService.notify_funds_released(deal)
        except Exception:
            pass
