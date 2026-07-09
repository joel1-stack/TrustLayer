from django import template

register = template.Library()


@register.filter
def mask_phone(phone):
    s = str(phone)
    if len(s) >= 8:
        return s[:4] + '****' + s[-2:]
    return s


@register.filter
def mask_api_key(key):
    s = str(key)
    if len(s) >= 12:
        return s[:8] + '****' + s[-4:]
    if len(s) >= 8:
        return s[:4] + '****'
    return '****'


@register.filter
def currency(value):
    try:
        v = float(value)
        return f'KES {v:,.2f}'
    except (ValueError, TypeError):
        return f'KES 0.00'


@register.filter
def status_badge(status):
    colors = {
        'CREATED': 'bg-gray-500',
        'PAYMENT_PENDING': 'bg-yellow-500',
        'COLLECTED': 'bg-blue-500',
        'WAITING': 'bg-orange-500',
        'READY': 'bg-teal-500',
        'SETTLING': 'bg-purple-500',
        'SETTLED': 'bg-green-500',
        'REFUNDED': 'bg-red-500',
        'CANCELLED': 'bg-red-700',
        'DISPUTED': 'bg-pink-500',
        'active': 'bg-green-500',
        'inactive': 'bg-red-500',
        'suspended': 'bg-orange-500',
        'completed': 'bg-green-500',
        'failed': 'bg-red-500',
        'processing': 'bg-blue-500',
        'running': 'bg-green-500',
        'healthy': 'bg-green-500',
        'connected': 'bg-green-500',
        'warning': 'bg-orange-500',
        'error': 'bg-red-500',
    }
    color = colors.get(status, 'bg-gray-400')
    return f'<span class="inline-block px-2 py-0.5 text-xs font-semibold rounded-full text-white {color}">{status}</span>'


@register.filter
def age_from_now(dt):
    if not dt:
        return ''
    from django.utils import timezone
    diff = timezone.now() - dt
    if diff.days > 0:
        return f'{diff.days}d ago'
    if diff.seconds >= 3600:
        return f'{diff.seconds // 3600}h ago'
    if diff.seconds >= 60:
        return f'{diff.seconds // 60}m ago'
    return f'{diff.seconds}s ago'


@register.filter
def get_item(d, key):
    return d.get(key, '')
