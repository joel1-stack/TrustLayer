from abc import ABC, abstractmethod

class PaymentProviderAdapter(ABC):
    """Every payment provider adapter must implement these three methods."""

    @abstractmethod
    def generate_link(self, amount, phone, reference, **kwargs):
        """Generate a payment link / checkout URL for the customer.
        
        Args:
            amount: Decimal amount to charge
            phone: Customer phone number (optional, for STK push)
            reference: Your internal reference (agreement_id)
        
        Returns:
            dict with at least:
                - 'success': bool
                - 'payment_url': str (the link customer clicks)
                - 'provider_reference': str (provider's transaction ID)
                - Or 'error': str if failed
        """
        pass

    @abstractmethod
    def send_payout(self, amount, phone, reference, **kwargs):
        """Send money to a recipient (payout/disbursement).
        
        Args:
            amount: Decimal amount to send
            phone: Recipient phone number
            reference: Your internal reference
        
        Returns:
            dict with:
                - 'success': bool
                - 'provider_tx_id': str
                - Or 'error': str if failed
        """
        pass

    @abstractmethod
    def handle_webhook(self, raw_payload):
        """Convert incoming provider webhook into standard format.
        
        Args:
            raw_payload: dict (the JSON body from the provider)
        
        Returns:
            dict with standard fields:
                - 'provider': str (e.g. 'intasend')
                - 'provider_transaction_id': str
                - 'internal_reference': str (the agreement_id you sent)
                - 'amount': Decimal
                - 'currency': str
                - 'status': 'completed' | 'failed'
                - 'phone': str (optional)
                - 'raw_payload': dict (original)
        """
        pass

    @abstractmethod
    def get_provider_name(self):
        """Return the provider identifier string."""
        pass
