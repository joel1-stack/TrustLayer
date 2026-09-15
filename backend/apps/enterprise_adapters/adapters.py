"""
Enterprise Data Adapters -- Abstract contracts and mock implementations.

Every organization (bank, telco, e-commerce) brings its own systems.
TrustLayer provides the adapter contract. Each organization implements
or plugs in their own adapter.

Architecture:
  Abstract Adapter Contract -> Mock Adapter -> Real Adapter (per org)

Adapter Types:
  - CustomerContextAdapter: Who is this customer?
  - ServiceContextAdapter: What service/product are they using?
  - BillingContextAdapter: What is their billing/payment status?
  - NetworkContextAdapter: What is the network/system status?
  - DeviceContextAdapter: What device are they using?
  - FraudSignalAdapter: Any fraud signals?
  - ActionAdapter: Execute remediation actions
  - CommunicationAdapter: Send notifications
"""
import random
import time
from abc import ABC, abstractmethod


# ============================================================================
# ABSTRACT ADAPTER CONTRACTS
# ============================================================================

class CustomerContextAdapter(ABC):
    """Who is this customer? What is their relationship with the organization?"""

    @abstractmethod
    def get_customer(self, customer_ref, metadata=None):
        """Return customer profile."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class ServiceContextAdapter(ABC):
    """What service/product is the customer using?"""

    @abstractmethod
    def get_service(self, customer_ref, metadata=None):
        """Return service/product status."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class BillingContextAdapter(ABC):
    """What is the customer's billing/payment status?"""

    @abstractmethod
    def get_billing(self, customer_ref, metadata=None):
        """Return billing/account status."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class NetworkContextAdapter(ABC):
    """What is the network/system status?"""

    @abstractmethod
    def get_network_state(self, customer_ref, metadata=None):
        """Return network/system state."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class DeviceContextAdapter(ABC):
    """What device is the customer using?"""

    @abstractmethod
    def get_device(self, customer_ref, metadata=None):
        """Return device info."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class FraudSignalAdapter(ABC):
    """Any fraud signals for this customer/case?"""

    @abstractmethod
    def get_fraud_signals(self, customer_ref, metadata=None):
        """Return fraud risk signals."""
        pass

    @abstractmethod
    def health_check(self):
        pass


class ActionAdapter(ABC):
    """Execute remediation actions on the organization's systems."""

    @abstractmethod
    def execute(self, action_type, customer_ref, parameters=None):
        """Execute an action and return result."""
        pass

    @abstractmethod
    def health_check(self):
        pass


# ============================================================================
# ORGANIZATION ADAPTER REGISTRY
# ============================================================================

class AdapterRegistry:
    """Registry of organization-specific adapters."""

    _adapters = {}

    @classmethod
    def register(cls, org_slug, adapter_type, adapter_instance):
        if org_slug not in cls._adapters:
            cls._adapters[org_slug] = {}
        cls._adapters[org_slug][adapter_type] = adapter_instance

    @classmethod
    def get(cls, org_slug, adapter_type):
        org_adapters = cls._adapters.get(org_slug, {})
        return org_adapters.get(adapter_type)

    @classmethod
    def get_all_for_org(cls, org_slug):
        return cls._adapters.get(org_slug, {})


# ============================================================================
# MOCK ADAPTERS -- TELCO (Safaricom/Airtel)
# ============================================================================

class MockTelcoCustomerAdapter(CustomerContextAdapter):
    PROFILES = [
        {
            'customer_id': 'SUB-001', 'name': 'John Doe',
            'msisdn': '+254712345678', 'status': 'ACTIVE',
            'plan': 'Data Bundle 1GB', 'plan_expiry': '2026-09-30',
            'registration_date': '2024-01-15', 'sim_swap_count': 0,
        },
        {
            'customer_id': 'SUB-002', 'name': 'Jane Smith',
            'msisdn': '+254798765432', 'status': 'INACTIVE',
            'plan': 'Data Bundle 500MB', 'plan_expiry': '2026-08-01',
            'registration_date': '2023-06-20', 'sim_swap_count': 1,
        },
    ]

    def get_customer(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(customer_ref or '') % len(self.PROFILES)
        return dict(self.PROFILES[idx])

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_customer', 'latency_ms': 12}


class MockTelcoServiceAdapter(ServiceContextAdapter):
    def get_service(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'service_type': 'MOBILE_DATA',
            'status': 'ACTIVE',
            'data_usage_mb': random.randint(100, 900),
            'data_limit_mb': 1024,
            'network_type': random.choice(['4G', '3G', '5G']),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_service', 'latency_ms': 8}


class MockTelcoBillingAdapter(BillingContextAdapter):
    PROFILES = [
        {'account_id': 'ACC-001', 'balance': 150.00, 'currency': 'KES',
         'last_payment_date': '2026-09-01', 'outstanding_balance': 0.00},
        {'account_id': 'ACC-002', 'balance': -25.00, 'currency': 'KES',
         'last_payment_date': '2026-07-15', 'outstanding_balance': 25.00},
    ]

    def get_billing(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        idx = hash(customer_ref or '') % len(self.PROFILES)
        return dict(self.PROFILES[idx])

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_billing', 'latency_ms': 8}


class MockTelcoNetworkAdapter(NetworkContextAdapter):
    def get_network_state(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'cell_tower_id': f'TWR-{random.randint(100,999)}',
            'tower_status': random.choice(['OPERATIONAL', 'DEGRADED']),
            'service_available': random.choice([True, False]),
            'signal_strength_dbm': random.randint(-100, -60),
            'network_type': random.choice(['4G', '3G']),
            'congestion_level': random.choice(['low', 'medium', 'high']),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_network', 'latency_ms': 15}


class MockTelcoDeviceAdapter(DeviceContextAdapter):
    def get_device(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'imei': f'860{random.randint(10000000000, 99999999999)}',
            'device_type': 'Smartphone',
            'manufacturer': random.choice(['Samsung', 'TECNO', 'Infinix', 'Apple']),
            'model': random.choice(['Galaxy A14', 'Spark 20', 'Note 12', 'iPhone 15']),
            'os_version': random.choice(['Android 14', 'Android 13', 'iOS 17']),
            'status': random.choice(['online', 'offline']),
            'data_enabled': random.choice([True, False]),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_device', 'latency_ms': 5}


class MockTelcoFraudAdapter(FraudSignalAdapter):
    def get_fraud_signals(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'risk_score': random.uniform(0.0, 1.0),
            'recent_sim_swap': random.choice([True, False]),
            'recent_device_swap': random.choice([True, False]),
            'account_takeover_risk': random.choice(['LOW', 'MEDIUM', 'HIGH']),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_fraud', 'latency_ms': 10}


class MockTelcoActionAdapter(ActionAdapter):
    def execute(self, action_type, customer_ref, parameters=None):
        time.sleep(random.uniform(0.01, 0.05))
        return {
            'success': True,
            'action': action_type,
            'result': f'Telco action {action_type} executed for {customer_ref}',
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'telco_action', 'latency_ms': 20}


# ============================================================================
# MOCK ADAPTERS -- BANKING (KCB/Equity)
# ============================================================================

class MockBankCustomerAdapter(CustomerContextAdapter):
    PROFILES = [
        {
            'customer_id': 'KCB-001', 'name': 'Peter Kamau',
            'account_type': 'SAVINGS', 'status': 'ACTIVE',
            'kyc_level': 'FULL', 'account_opened': '2022-03-15',
            'branch': 'Westlands', 'relationship_manager': 'Agent-001',
        },
        {
            'customer_id': 'KCB-002', 'name': 'Mary Wanjiku',
            'account_type': 'CURRENT', 'status': 'ACTIVE',
            'kyc_level': 'FULL', 'account_opened': '2021-08-20',
            'branch': 'CBD', 'relationship_manager': 'Agent-002',
        },
    ]

    def get_customer(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(customer_ref or '') % len(self.PROFILES)
        return dict(self.PROFILES[idx])

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'bank_customer', 'latency_ms': 15}


class MockBankServiceAdapter(ServiceContextAdapter):
    def get_service(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'service_type': random.choice(['MOBILE_BANKING', 'CARD', 'LOAN', 'M_PESA']),
            'status': 'ACTIVE',
            'last_login': '2026-09-14T10:30:00Z',
            'devices_registered': 2,
            'alerts_enabled': True,
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'bank_service', 'latency_ms': 10}


class MockBankBillingAdapter(BillingContextAdapter):
    PROFILES = [
        {'account_id': 'KCB-ACC-001', 'balance': 45000.00, 'currency': 'KES',
         'last_transaction': '2026-09-14', 'pending_transactions': 2,
         'overdraft_limit': 10000.00},
        {'account_id': 'KCB-ACC-002', 'balance': 1200.00, 'currency': 'KES',
         'last_transaction': '2026-09-13', 'pending_transactions': 0,
         'overdraft_limit': 0.00},
    ]

    def get_billing(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        idx = hash(customer_ref or '') % len(self.PROFILES)
        return dict(self.PROFILES[idx])

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'bank_billing', 'latency_ms': 10}


class MockBankFraudAdapter(FraudSignalAdapter):
    def get_fraud_signals(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'risk_score': random.uniform(0.0, 1.0),
            'recent_password_change': random.choice([True, False]),
            'recent_device_change': random.choice([True, False]),
            'suspicious_transaction_count': random.randint(0, 3),
            'account_takeover_risk': random.choice(['LOW', 'MEDIUM', 'HIGH']),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'bank_fraud', 'latency_ms': 10}


class MockBankActionAdapter(ActionAdapter):
    def execute(self, action_type, customer_ref, parameters=None):
        time.sleep(random.uniform(0.01, 0.05))
        return {
            'success': True,
            'action': action_type,
            'result': f'Bank action {action_type} executed for {customer_ref}',
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'bank_action', 'latency_ms': 25}


# ============================================================================
# MOCK ADAPTERS -- E-COMMERCE (Jumia)
# ============================================================================

class MockEcommerceCustomerAdapter(CustomerContextAdapter):
    PROFILES = [
        {
            'customer_id': 'JUM-001', 'name': 'Alice Ochieng',
            'status': 'ACTIVE', 'member_since': '2024-05-10',
            'orders_count': 12, 'avg_rating': 4.5,
            'preferred_payment': 'M_PESA',
        },
        {
            'customer_id': 'JUM-002', 'name': 'Bob Mutua',
            'status': 'ACTIVE', 'member_since': '2025-01-20',
            'orders_count': 3, 'avg_rating': 4.0,
            'preferred_payment': 'CARD',
        },
    ]

    def get_customer(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.05))
        idx = hash(customer_ref or '') % len(self.PROFILES)
        return dict(self.PROFILES[idx])

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'ecommerce_customer', 'latency_ms': 8}


class MockEcommerceServiceAdapter(ServiceContextAdapter):
    def get_service(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'service_type': 'MARKETPLACE',
            'status': 'ACTIVE',
            'recent_orders': random.randint(1, 5),
            'pending_deliveries': random.randint(0, 2),
            'active_disputes': random.randint(0, 1),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'ecommerce_service', 'latency_ms': 6}


class MockEcommerceBillingAdapter(BillingContextAdapter):
    def get_billing(self, customer_ref, metadata=None):
        time.sleep(random.uniform(0.01, 0.03))
        return {
            'wallet_balance': random.uniform(0, 5000),
            'currency': 'KES',
            'pending_refunds': random.randint(0, 2),
            'last_order_amount': random.uniform(500, 15000),
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'ecommerce_billing', 'latency_ms': 6}


class MockEcommerceActionAdapter(ActionAdapter):
    def execute(self, action_type, customer_ref, parameters=None):
        time.sleep(random.uniform(0.01, 0.05))
        return {
            'success': True,
            'action': action_type,
            'result': f'E-commerce action {action_type} executed for {customer_ref}',
        }

    def health_check(self):
        return {'status': 'healthy', 'adapter': 'ecommerce_action', 'latency_ms': 15}


# ============================================================================
# REGISTER MOCK ADAPTERS
# ============================================================================

def register_default_adapters():
    """Register all mock adapters for development."""
    # Telco adapters
    AdapterRegistry.register('safaricom', 'customer', MockTelcoCustomerAdapter())
    AdapterRegistry.register('safaricom', 'service', MockTelcoServiceAdapter())
    AdapterRegistry.register('safaricom', 'billing', MockTelcoBillingAdapter())
    AdapterRegistry.register('safaricom', 'network', MockTelcoNetworkAdapter())
    AdapterRegistry.register('safaricom', 'device', MockTelcoDeviceAdapter())
    AdapterRegistry.register('safaricom', 'fraud', MockTelcoFraudAdapter())
    AdapterRegistry.register('safaricom', 'action', MockTelcoActionAdapter())

    AdapterRegistry.register('airtel', 'customer', MockTelcoCustomerAdapter())
    AdapterRegistry.register('airtel', 'service', MockTelcoServiceAdapter())
    AdapterRegistry.register('airtel', 'billing', MockTelcoBillingAdapter())
    AdapterRegistry.register('airtel', 'network', MockTelcoNetworkAdapter())
    AdapterRegistry.register('airtel', 'device', MockTelcoDeviceAdapter())
    AdapterRegistry.register('airtel', 'fraud', MockTelcoFraudAdapter())
    AdapterRegistry.register('airtel', 'action', MockTelcoActionAdapter())

    # Bank adapters
    AdapterRegistry.register('kcb', 'customer', MockBankCustomerAdapter())
    AdapterRegistry.register('kcb', 'service', MockBankServiceAdapter())
    AdapterRegistry.register('kcb', 'billing', MockBankBillingAdapter())
    AdapterRegistry.register('kcb', 'fraud', MockBankFraudAdapter())
    AdapterRegistry.register('kcb', 'action', MockBankActionAdapter())

    AdapterRegistry.register('equity', 'customer', MockBankCustomerAdapter())
    AdapterRegistry.register('equity', 'service', MockBankServiceAdapter())
    AdapterRegistry.register('equity', 'billing', MockBankBillingAdapter())
    AdapterRegistry.register('equity', 'fraud', MockBankFraudAdapter())
    AdapterRegistry.register('equity', 'action', MockBankActionAdapter())

    # E-commerce adapters
    AdapterRegistry.register('jumia', 'customer', MockEcommerceCustomerAdapter())
    AdapterRegistry.register('jumia', 'service', MockEcommerceServiceAdapter())
    AdapterRegistry.register('jumia', 'billing', MockEcommerceBillingAdapter())
    AdapterRegistry.register('jumia', 'action', MockEcommerceActionAdapter())


# Auto-register on import
register_default_adapters()
