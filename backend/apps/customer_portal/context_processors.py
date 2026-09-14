from .models import Customer


def portal_verified(request):
    cid = request.session.get('customer_id')
    if cid:
        try:
            cust = Customer.objects.only('email_verified').get(customer_id=cid)
            request.session['customer_email_verified'] = cust.email_verified
        except Customer.DoesNotExist:
            pass
    return {}
