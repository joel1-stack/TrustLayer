# TrustLayer

**Escrow infrastructure for African digital commerce.**

M-Pesa moves money. TrustLayer controls *when* it moves.

## The Problem

| Issue                               | Reality             |
| ----------------------------------- | ------------------- |
| Buyer pays → seller disappears      | No enforcement      |
| Disputes take months                | Courts are too slow |
| Marketplaces take no responsibility | Zero protection     |

## The Solution

```text
PENDING → HELD → DELIVERED → RELEASED
    ↓         ↓
REFUNDED   DISPUTED → RESOLVED
```

Funds are held conditionally until delivery is confirmed or disputes are resolved.

* 48h dispute SLA
* Escrow-based payment flow
* Bad-faith dispute penalties

## What Works Now

* ✅ Merchant registration and dashboard
* ✅ Direct M-Pesa STK Push integration
* ✅ Escrow transaction lifecycle
* ✅ Seller delivery confirmation
* ✅ Buyer dispute handling
* ✅ Dockerized deployment workflow

## Tech Stack

* Python 3.12
* Django + Django REST Framework
* PostgreSQL
* Redis
* Celery
* Docker
* M-Pesa Daraja API

## Architecture

Domain-oriented backend structure:

* merchants
* payments
* escrow
* disputes
* notifications
* webhooks
* compliance

## Contact

**Joel Kaunda**
Backend Engineer · APIs · Payment Systems · Fintech
Nairobi, Kenya

LinkedIn: linkedin.com/in/joelkaunda-dev8376
Email: [joelkaunda15@gmail.com](mailto:joelkaunda15@gmail.com)

---

**TrustLayer** — Safe payments. Real trust. Built for Africa.
