"""
Enterprise Data Adapters — Mock implementations for telecom service assurance.

Each adapter simulates querying a real enterprise system (HLR, billing, network, device).
Replace with real API calls when access is granted.
"""
import random
import time
from abc import ABC, abstractmethod


class EnterpriseDataAdapter(ABC):
    @abstractmethod
    def query(self, case_id, metadata=None):
        pass

    @abstractmethod
    def health_check(self):
        pass


class MockSubscriberAdapter(EnterpriseDataAdapter):
    """Simulates HLR/HSS subscriber data queries."""

    SUBSCRIBER_PROFILES = [
        {
            'subscriber_id': 'SUB-001',
            'name': 'John Doe',
            'msisdn': '+254712345678',
            'status': 'ACTIVE',
            'plan': 'Data Bundle 1GB',
            'plan_expiry': '2026-09-30',
            'registration_date': '2024-01-15',
            'sim_swap_count': 0,
            'imei': '353456789012345',
        },
        {
            'subscriber_id': 'SUB-002',
            'name': 'Jane Smith',
            'msisdn': '+254798765432',
            'status': 'INACTIVE',
            'plan': 'Data Bundle 500MB',
            'plan_expiry': '2026-08-01',
            'registration_date': '2023-06-20',
            'sim_swap_count': 1,
            'imei': '860123456789012',
        },
    ]

    def query(self, case_id, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(case_id) % len(self.SUBSCRIBER_PROFILES)
        profile = dict(self.SUBSCRIBER_PROFILES[idx])
        profile['query_timestamp'] = time.time()
        return profile

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'subscriber', 'latency_ms': 12}


class MockBillingAdapter(EnterpriseDataAdapter):
    """Simulates billing system queries (usage, balance, payment history)."""

    BILLING_PROFILES = [
        {
            'account_id': 'ACC-001',
            'balance': 150.00,
            'currency': 'KES',
            'last_payment_date': '2026-09-01',
            'last_payment_amount': 500.00,
            'outstanding_balance': 0.00,
            'data_used_mb': 750,
            'data_limit_mb': 1024,
            'billing_cycle': 'monthly',
            'auto_renew': True,
        },
        {
            'account_id': 'ACC-002',
            'balance': -25.00,
            'currency': 'KES',
            'last_payment_date': '2026-07-15',
            'last_payment_amount': 300.00,
            'outstanding_balance': 25.00,
            'data_used_mb': 500,
            'data_limit_mb': 512,
            'billing_cycle': 'monthly',
            'auto_renew': False,
        },
    ]

    def query(self, case_id, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(case_id) % len(self.BILLING_PROFILES)
        profile = dict(self.BILLING_PROFILES[idx])
        profile['query_timestamp'] = time.time()
        return profile

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'billing', 'latency_ms': 8}


class MockNetworkAdapter(EnterpriseDataAdapter):
    """Simulates network performance and outage data."""

    NETWORK_STATES = [
        {
            'cell_tower_id': 'TWR-001',
            'tower_status': 'OPERATIONAL',
            'service_available': True,
            'signal_strength_dbm': -75,
            'network_type': '4G',
            'congestion_level': 'low',
            'active_outages': [],
            'last_maintenance': '2026-09-10',
        },
        {
            'cell_tower_id': 'TWR-002',
            'tower_status': 'DEGRADED',
            'service_available': False,
            'signal_strength_dbm': -95,
            'network_type': '3G',
            'congestion_level': 'high',
            'active_outages': [
                {'type': 'power_failure', 'started': '2026-09-14T02:00:00Z', 'eta': '2026-09-14T08:00:00Z'}
            ],
            'last_maintenance': '2026-08-01',
        },
    ]

    def query(self, case_id, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(case_id) % len(self.NETWORK_STATES)
        state = dict(self.NETWORK_STATES[idx])
        state['query_timestamp'] = time.time()
        return state

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'network', 'latency_ms': 15}


class MockDeviceAdapter(EnterpriseDataAdapter):
    """Simulates device status and IMEI queries."""

    DEVICE_PROFILES = [
        {
            'imei': '353456789012345',
            'device_type': 'Smartphone',
            'manufacturer': 'Samsung',
            'model': 'Galaxy A14',
            'os_version': 'Android 14',
            'last_seen': '2026-09-14T10:30:00Z',
            'status': 'online',
            'data_enabled': True,
            'roaming': False,
        },
        {
            'imei': '860123456789012',
            'device_type': 'Smartphone',
            'manufacturer': 'TECNO',
            'model': 'Spark 20',
            'os_version': 'Android 13',
            'last_seen': '2026-09-10T08:15:00Z',
            'status': 'offline',
            'data_enabled': False,
            'roaming': False,
        },
    ]

    def query(self, case_id, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(case_id) % len(self.DEVICE_PROFILES)
        profile = dict(self.DEVICE_PROFILES[idx])
        profile['query_timestamp'] = time.time()
        return profile

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'device', 'latency_ms': 5}
