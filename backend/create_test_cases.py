#!/usr/bin/env python
"""
Create test cases for TrustLayer v1 demo
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()

from apps.agreements.models import Case, CaseTimeline, CaseMessage, CaseEvidence
from django.utils import timezone

def create_test_cases():
    # Clear existing cases
    Case.objects.all().delete()
    
    # Case 1: Transaction Dispute (INVESTIGATING)
    case1 = Case.objects.create(
        case_id='CASE-9921',
        problem_type='TRANSACTION_DISPUTE',
        txn_id='TXN-8839201',
        amount=50000,
        currency='KES',
        description='I did not make this payment. I had my card with me the entire day.',
        date_occurred=timezone.now().date(),
        customer_name='John Doe',
        customer_phone='+254712345678',
        customer_email='john.doe@example.com',
        priority='HIGH',
        status='INVESTIGATING',
        status_code_value=30000,
    )
    
    CaseTimeline.objects.create(
        case=case1,
        from_status='',
        to_status='OPEN',
        reason='Case created by customer',
        triggered_by='customer'
    )
    
    CaseTimeline.objects.create(
        case=case1,
        from_status='OPEN',
        to_status='INVESTIGATING',
        reason='Agent started investigation',
        triggered_by='agent'
    )
    
    CaseMessage.objects.create(
        case=case1,
        sender='John Doe',
        sender_type='customer',
        text='I did not make this payment. I had my card with me the entire day.'
    )
    
    CaseMessage.objects.create(
        case=case1,
        sender='Fraud Agent',
        sender_type='agent',
        text='We are reviewing the transaction details. Please confirm whether your card or device was in your possession at the time of the transaction.'
    )
    
    # Case 2: Payment Issue (INVESTIGATING)
    case2 = Case.objects.create(
        case_id='CASE-9920',
        problem_type='PAYMENT_ISSUE',
        txn_id='TXN-8839200',
        amount=15000,
        currency='KES',
        description='Payment was deducted twice from my account.',
        date_occurred=timezone.now().date(),
        customer_name='Jane Smith',
        customer_email='jane.smith@example.com',
        priority='NORMAL',
        status='INVESTIGATING',
        status_code_value=30000,
    )
    
    CaseTimeline.objects.create(
        case=case2,
        from_status='',
        to_status='OPEN',
        reason='Case created by customer',
        triggered_by='customer'
    )
    
    # Case 3: Account Security (ESCALATED)
    case3 = Case.objects.create(
        case_id='CASE-9919',
        problem_type='ACCOUNT_ISSUE',
        txn_id='ACC-123456',
        amount=0,
        currency='KES',
        description='Unauthorized login attempts on my account.',
        date_occurred=timezone.now().date(),
        customer_name='Peter Kamau',
        customer_phone='+254700123456',
        priority='CRITICAL',
        status='ESCALATED',
        status_code_value=40000,
    )
    
    CaseTimeline.objects.create(
        case=case3,
        from_status='',
        to_status='OPEN',
        reason='Case created by customer',
        triggered_by='customer'
    )
    
    CaseTimeline.objects.create(
        case=case3,
        from_status='OPEN',
        to_status='ESCALATED',
        reason='Critical security issue',
        triggered_by='system'
    )
    
    print("✅ Created 3 test cases:")
    print("  - CASE-9921 (Transaction Dispute, HIGH, INVESTIGATING)")
    print("  - CASE-9920 (Payment Issue, NORMAL, INVESTIGATING)")
    print("  - CASE-9919 (Account Security, CRITICAL, ESCALATED)")
    print(f"\n🔗 View at: https://miranda-stockish-spacially.ngrok-free.dev/")

if __name__ == '__main__':
    create_test_cases()
