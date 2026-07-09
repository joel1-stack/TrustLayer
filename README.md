<p align="center">
  <img src="https://img.icons8.com/fluency/96/shield.png" width="64"/>
</p>

<h1 align="center">TrustLayer</h1>

<p align="center">
  <b>Trust orchestration platform for African commerce.</b><br>
  6 interoperable engines — Agreement, State Machine, Condition, Ledger, Settlement, Notification.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-2ea043?logo=python">
  <img src="https://img.shields.io/badge/django-4.2-0c4b33?logo=django">
  <img src="https://img.shields.io/badge/IntaSend-integrated-0066cc">
  <img src="https://img.shields.io/badge/M--Pesa-integrated-00a859">
  <img src="https://img.shields.io/badge/Stripe-integrated-6772e5">
</p>

---

## What it solves

African commerce runs on trust. Buyers pay, sellers deliver — but when something goes wrong, there's no middle layer. TrustLayer is that layer. It holds payment instructions in a conditional state machine, releases only when conditions are met, and settles through M-Pesa, IntaSend, or Stripe.

Built for SACCOS, hospitals, e-commerce platforms, land companies, and any marketplace that needs programmable trust.

---

## Architecture

```
                          ┌─────────────────────────────────────┐
                          │        Orchestration Engine         │
                          └───┬─────┬─────┬─────┬─────┬─────┬───┘
              ┌───────────────┼─────┼─────┼─────┼─────┼─────┼───────────────┐
              │   Agreement   │State│Cond.│Ledger│Settl.│Notif.│              │
              │    Engine     │Mach.│Engine│Engine│Engine│Engine│              │
              └───────┬───────┘     │      │      │      │      │              │
         ┌────────────┴──────────────────────────────────────┴──────────────┐
         │              Payment Provider Adapters (pluggable)               │
         │    IntaSend    │    M-Pesa (Daraja)    │    Stripe    │    ...    │
         └──────────────────────────────────────────────────────────────────┘
```

**Two webhook directions:**
1. **TrustLayer → Developer**: Outgoing POST to `agreement.developer_webhook_url` for lifecycle events
2. **Provider → TrustLayer**: Incoming POST to `/webhooks/{intasend,mpesa,stripe}/`

---

## API Endpoints

| Engine | Endpoints |
|---|---|
| **Agreement** | POST `/api/agreements/` — create, GET `/api/agreements/<id>/` — read |
| **Condition** | POST `/api/conditions/` — add, POST `/api/conditions/<id>/met/` — mark met |
| **Ledger** | GET `/api/ledger/<agreement_id>/` — entries |
| **Settlement** | POST `/api/settlements/<agreement_id>/trigger/` — trigger |
| **Notification** | GET `/api/notifications/<agreement_id>/` — list events |
| **Payments** | POST `/api/payments/link/` — generate payment link |
| **Webhooks** | POST `/webhooks/intasend/`, `/webhooks/mpesa/`, `/webhooks/stripe/` |

---

## Agreement Flow

```
CREATED → PAYMENT_PENDING → COLLECTED → WAITING → READY → SETTLING → SETTLED
                                                              ↘ REFUNDED
                                                    CANCELLED at any point
```

---

## Quick Start

```bash
cp .env.example .env
docker compose up -d
docker exec trustlayer_api python manage.py migrate
```

---

<p align="center">
  <sub>Built for Africa. Safe payments. Real trust.</sub>
</p>
