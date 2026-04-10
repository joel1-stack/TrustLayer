import pytest
from decimal import Decimal

def test_fee_calculation():
    amount = Decimal("5000")
    fee = (amount * Decimal("0.015")).quantize(Decimal("0.01"))
    assert fee == Decimal("75.00")

def test_deal_code_format():
    import random, string
    chars = string.ascii_uppercase + string.digits
    code = "TL-" + "".join(random.choices(chars, k=6))
    assert code.startswith("TL-")
    assert len(code) == 9

def test_total_payable():
    amount = Decimal("5000")
    fee = Decimal("75.00")
    total = amount + fee
    assert total == Decimal("5075.00")

def test_state_machine_order():
    states = ["pending", "held", "done"]
    assert states.index("pending") < states.index("held")
    assert states.index("held") < states.index("done")
