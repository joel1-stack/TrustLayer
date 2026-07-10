from .intasend import IntaSendAdapter
from .mpesa import MpesaAdapter
from .stripe import StripeAdapter
from .bank_transfer import BankTransferAdapter

_adapter_registry = {}

def register_adapter(adapter):
    _adapter_registry[adapter.get_provider_name()] = adapter

def get_adapter(provider_name):
    adapter = _adapter_registry.get(provider_name)
    if not adapter:
        raise ValueError(f"Unknown payment provider: {provider_name}. Available: {list(_adapter_registry.keys())}")
    return adapter

def list_providers():
    return list(_adapter_registry.keys())

# Register built-in adapters
register_adapter(IntaSendAdapter())
register_adapter(MpesaAdapter())
register_adapter(StripeAdapter())
register_adapter(BankTransferAdapter())
