from celery import shared_task
from django.utils import timezone


@shared_task
def auto_release_held_deals():
    """
    Runs every 15 minutes via Celery Beat.
    Releases any HELD deal whose auto_release_at has passed (48h window).
    """
    from apps.escrow.models import EscrowDeal
    from apps.notifications.services import NotificationService

    overdue = EscrowDeal.objects.filter(
        status='HELD',
        auto_release_at__lte=timezone.now(),
    )

    for deal in overdue:
        deal.status      = 'RELEASED'
        deal.released_at = timezone.now()
        deal.save(update_fields=['status', 'released_at'])
        try:
            NotificationService.notify_funds_released(deal)
        except Exception:
            pass
