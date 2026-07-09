from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .services import LedgerService
from .models import LedgerEntry

@require_http_methods(["GET"])
def get_entries(request, agreement_id):
    from apps.agreements.models import Agreement
    agreement = Agreement.objects.filter(agreement_id=agreement_id).first()
    if not agreement:
        return JsonResponse({'error': 'Agreement not found'}, status=404)
    entries = LedgerEntry.objects.filter(agreement=agreement).values(
        'entry_id', 'entry_type', 'amount', 'currency', 'balance_before', 'balance_after',
        'reference', 'description', 'created_at'
    )
    return JsonResponse(list(entries), safe=False)

@require_http_methods(["GET"])
def get_balance(request, party_id):
    from apps.agreements.models import AgreementParty
    party = AgreementParty.objects.filter(id=party_id).first()
    if not party:
        return JsonResponse({'error': 'Party not found'}, status=404)
    balance = LedgerService.get_balance(party)
    return JsonResponse({
        'party_id': party_id,
        'party_name': party.name,
        'balance': str(balance),
    })