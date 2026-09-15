STATUS_CODES = {
    'OPEN': 10000,
    'EVIDENCE_COLLECTION': 15000,
    'INVESTIGATING': 20000,
    'RESOLUTION_RECORDED': 25000,
    'ESCALATED': 27000,
    'VERIFYING': 30000,
    'RESOLVED': 35000,
    'REOPENED': 37000,
    'CLOSED': 40000,
}

STATUS_CATEGORIES = {
    'OPEN': 'active',
    'EVIDENCE_COLLECTION': 'active',
    'INVESTIGATING': 'active',
    'RESOLUTION_RECORDED': 'active',
    'ESCALATED': 'active',
    'VERIFYING': 'active',
    'RESOLVED': 'terminal',
    'REOPENED': 'active',
    'CLOSED': 'terminal',
}

VALID_TRANSITIONS = {
    'OPEN': ['EVIDENCE_COLLECTION', 'INVESTIGATING', 'CLOSED'],
    'EVIDENCE_COLLECTION': ['INVESTIGATING', 'CLOSED'],
    'INVESTIGATING': ['RESOLUTION_RECORDED', 'ESCALATED', 'CLOSED'],
    'RESOLUTION_RECORDED': ['VERIFYING', 'REOPENED'],
    'ESCALATED': ['INVESTIGATING', 'RESOLUTION_RECORDED', 'CLOSED'],
    'VERIFYING': ['RESOLVED', 'REOPENED'],
    'RESOLVED': ['CLOSED'],
    'REOPENED': ['INVESTIGATING'],
    'CLOSED': [],
}

TERMINAL_STATES = {'RESOLVED', 'CLOSED'}

PROBLEM_TYPES = [
    ('TRANSACTION_DISPUTE', 'I don\'t recognize a transaction'),
    ('PAYMENT_PROBLEM', 'Payment problem'),
    ('ACCOUNT_PROBLEM', 'Account problem'),
    ('OTHER', 'Other'),
]

RESOLUTION_TYPES = [
    ('CONFIRMED_FRAUD', 'Confirmed fraud'),
    ('TRANSACTION_LEGITIMATE', 'Transaction legitimate'),
    ('CUSTOMER_ERROR', 'Customer error'),
    ('UNABLE_TO_DETERMINE', 'Unable to determine'),
]
