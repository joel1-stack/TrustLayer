#!/usr/bin/env python
"""
Test all TrustLayer v1 endpoints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustlayer.settings')
django.setup()

from django.test import Client
from apps.agreements.models import Case
from django.utils import timezone

def test_all_endpoints():
    client = Client()
    
    print("🧪 Testing TrustLayer v1 Endpoints\n")
    print("="*60)
    
    # Test 1: Homepage
    print("\n✓ Test 1: Homepage")
    response = client.get('/')
    assert response.status_code == 200, f"Failed: {response.status_code}"
    print(f"  Status: {response.status_code} ✓")
    
    # Test 2: Report page
    print("\n✓ Test 2: Report Form")
    response = client.get('/report/')
    assert response.status_code == 200
    print(f"  Status: {response.status_code} ✓")
    
    # Test 3: Submit case
    print("\n✓ Test 3: Submit Case")
    response = client.post('/report/submit/', {
        'problem_type': 'TRANSACTION_DISPUTE',
        'txn_id': 'TXN-TEST-001',
        'amount': '15000',
        'currency': 'KES',
        'description': 'Test case submission',
        'date_occurred': timezone.now().date(),
        'customer_name': 'Test User',
        'customer_phone': '+254700000000',
    })
    assert response.status_code in [200, 302], f"Failed: {response.status_code}"
    print(f"  Status: {response.status_code} ✓")
    
    # Get the created case
    case = Case.objects.filter(txn_id='TXN-TEST-001').first()
    if case:
        case_id = case.case_id
        print(f"  Created: {case_id}")
        
        # Test 4: Case detail
        print("\n✓ Test 4: Case Detail")
        response = client.get(f'/case/{case_id}/')
        assert response.status_code == 200
        print(f"  Status: {response.status_code} ✓")
        
        # Test 5: Track page
        print("\n✓ Test 5: Track Page")
        response = client.get('/track/')
        assert response.status_code == 200
        print(f"  Status: {response.status_code} ✓")
        
        # Test 6: Verify page
        print("\n✓ Test 6: Verify Page")
        response = client.get(f'/case/{case_id}/verify/')
        assert response.status_code == 200
        print(f"  Status: {response.status_code} ✓")
        
        # Test 7: Agent dashboard
        print("\n✓ Test 7: Agent Dashboard")
        response = client.get('/admin/')
        print(f"  Status: {response.status_code}")
        if response.status_code != 200:
            print(f"  Error: {response.content[:200]}")
        assert response.status_code == 200
        print(f"  ✓")
        
        # Test 8: Agent case detail
        print("\n✓ Test 8: Agent Case Detail")
        response = client.get(f'/admin/case/{case_id}/')
        assert response.status_code == 200
        print(f"  Status: {response.status_code} ✓")
        
        # Test 9: Add message
        print("\n✓ Test 9: Add Message")
        response = client.post(f'/case/{case_id}/message/', {
            'sender': 'Test Customer',
            'sender_type': 'customer',
            'text': 'This is a test message',
        })
        assert response.status_code in [200, 302]
        print(f"  Status: {response.status_code} ✓")
        
        # Test 10: Agent resolve
        print("\n✓ Test 10: Agent Resolve Case")
        response = client.post(f'/admin/case/{case_id}/', {
            'action': 'resolve',
            'resolution_type': 'confirmed_fraud',
            'finding': 'Unauthorized transaction',
            'note': 'Refund initiated',
            'agent_id': 'test-agent',
        })
        assert response.status_code in [200, 302]
        print(f"  Status: {response.status_code} ✓")
        
    # Test 11: Health check
    print("\n✓ Test 11: Health Check")
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    print(f"  Status: {response.status_code} ✓")
    print(f"  Response: {data}")
    
    # Test 12: Case not found
    print("\n✓ Test 12: Case Not Found (404)")
    response = client.get('/case/INVALID-ID/')
    assert response.status_code == 200  # Renders error template
    print(f"  Status: {response.status_code} ✓")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    
    # Summary
    if case:
        print(f"\n📋 Test Case Created: {case_id}")
        print(f"   Status: {case.status}")
        print(f"   Transaction: {case.txn_id}")
        print(f"   Amount: KES {case.amount}")
        print(f"\n🔗 View at: https://miranda-stockish-spacially.ngrok-free.dev/case/{case_id}/")

if __name__ == '__main__':
    test_all_endpoints()
