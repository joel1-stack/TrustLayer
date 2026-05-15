import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta
from .models import Dispute, DisputeMessage
from apps.escrow.models import EscrowDeal


@csrf_exempt
@require_POST
def open_dispute(request):
    try:
        data      = json.loads(request.body)
        deal_code = data.get('deal_code')
        reason    = data.get('reason', '')
        opened_by = data.get('opened_by', 'BUYER')
        evidence  = data.get('evidence', '')

        deal = EscrowDeal.objects.get(deal_code=deal_code)

        if hasattr(deal, 'dispute'):
            return JsonResponse({'success': False, 'error': 'Dispute already exists'}, status=400)

        dispute = Dispute.objects.create(
            deal=deal,
            opened_by=opened_by,
            reason=reason,
            buyer_evidence=evidence if opened_by == 'BUYER' else '',
            seller_evidence=evidence if opened_by == 'SELLER' else '',
            evidence_deadline=timezone.now() + timedelta(hours=24),
        )
        deal.status = 'DISPUTED'
        deal.save()

        return JsonResponse({
            'success':          True,
            'dispute_id':       str(dispute.id),
            'status':           dispute.status,
            'evidence_deadline': dispute.evidence_deadline.isoformat(),
            'message':          'Dispute opened. You have 24 hours to submit evidence.',
        })
    except EscrowDeal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Deal not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def submit_evidence(request):
    try:
        data         = json.loads(request.body)
        dispute_id   = data.get('dispute_id')
        submitted_by = data.get('submitted_by')
        evidence     = data.get('evidence', '')
        files        = data.get('files', [])

        dispute = Dispute.objects.get(id=dispute_id)

        if submitted_by == 'BUYER':
            dispute.buyer_evidence       = evidence
            dispute.buyer_evidence_files = files
        else:
            dispute.seller_evidence       = evidence
            dispute.seller_evidence_files = files

        dispute.status = 'EVIDENCE_SUBMITTED'
        dispute.save()

        DisputeMessage.objects.create(
            dispute=dispute,
            sender=submitted_by,
            message=f"Evidence submitted: {evidence[:200]}",
        )
        return JsonResponse({'success': True, 'message': 'Evidence submitted'})
    except Dispute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dispute not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
def dispute_status(request, dispute_id):
    try:
        d = Dispute.objects.get(id=dispute_id)
        return JsonResponse({'success': True, 'dispute': {
            'id':               str(d.id),
            'deal_code':        d.deal.deal_code,
            'status':           d.status,
            'opened_by':        d.opened_by,
            'reason':           d.reason,
            'buyer_evidence':   d.buyer_evidence,
            'seller_evidence':  d.seller_evidence,
            'resolution_notes': d.resolution_notes,
            'opened_at':        d.opened_at.isoformat(),
            'evidence_deadline': d.evidence_deadline.isoformat() if d.evidence_deadline else None,
            'resolved_at':      d.resolved_at.isoformat() if d.resolved_at else None,
        }})
    except Dispute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dispute not found'}, status=404)


@csrf_exempt
@require_POST
def admin_resolve(request):
    try:
        data            = json.loads(request.body)
        dispute_id      = data.get('dispute_id')
        resolution      = data.get('resolution')   # 'BUYER' or 'SELLER'
        notes           = data.get('notes', '')
        penalty_percent = data.get('penalty', 10)

        # Admin token check
        from django.conf import settings
        if request.META.get('HTTP_X_ADMIN_TOKEN') != getattr(settings, 'TRUSTLAYER_ADMIN_TOKEN', ''):
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        dispute        = Dispute.objects.get(id=dispute_id)
        penalty_amount = (dispute.deal.amount * penalty_percent) / 100

        dispute.status           = f'RESOLVED_{resolution}'
        dispute.resolution_notes = notes
        dispute.penalty_amount   = penalty_amount
        dispute.penalty_to       = 'BUYER' if resolution == 'SELLER' else 'SELLER'
        dispute.resolved_at      = timezone.now()
        dispute.save()

        dispute.deal.status = 'REFUNDED' if resolution == 'BUYER' else 'RELEASED'
        dispute.deal.save()

        return JsonResponse({
            'success':        True,
            'message':        f'Dispute resolved in favor of {resolution}',
            'penalty_amount': str(penalty_amount),
            'penalty_to':     dispute.penalty_to,
        })
    except Dispute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dispute not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
