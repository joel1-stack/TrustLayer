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
  <img src="https://img.shields.io/badge/celery-✅-3fb950">
  <img src="https://img.shields.io/badge/IntaSend-integrated-0066cc">
  <img src="https://img.shields.io/badge/M--Pesa-integrated-00a859">
  <img src="https://img.shields.io/badge/Stripe-integrated-6772e5">
</p>

---

## Architecture

```
                          ┌─────────────────────────────────────┐
                          │        Orchestration Engine         │
                          │  (conducts the full agreement flow) │
                          └───┬─────┬─────┬─────┬─────┬─────┬───┘
                              │     │     │     │     │     │
              ┌───────────────┼─────┼─────┼─────┼─────┼─────┼───────────────┐
              │   Agreement   │State│Cond.│Ledger│Settl.│Notif.│              │
              │    Engine     │Mach.│Engine│Engine│Engine│Engine│              │
              │  (creates +   │     │      │      │      │      │              │
              │   manages     │     │      │      │      │      │              │
              │  agreements)  │     │      │      │      │      │              │
              └───────┬───────┘     │      │      │      │      │              │
                      │             │      │      │      │      │              │
         ┌────────────┴──────────────────────────────────────┴──────────────┐
         │              Payment Provider Adapters (pluggable)               │
         │    IntaSend    │    M-Pesa (Daraja)    │    Stripe    │    ...    │
         └──────────────────────────────────────────────────────────────────┘
```

**Two webhook directions:**
1. **TrustLayer → Developer**: Outgoing `POST` to `agreement.developer_webhook_url` for lifecycle events
2. **Provider → TrustLayer**: Incoming `POST` to `/webhooks/{intasend,mpesa,stripe}/`

---

## Engines & API Endpoints

| Engine | Endpoints |
|---|---|
| **Agreement** | `POST /api/agreements/` — create, `GET /api/agreements/<id>/` — read, `POST /api/agreements/<id>/party/` — add party |
| **Condition** | `POST /api/conditions/` — add condition, `POST /api/conditions/<id>/met/` — mark met |
| **Ledger** | `GET /api/ledger/<agreement_id>/` — entries, `GET /api/ledger/balance/<party_id>/` — balance |
| **Settlement** | `POST /api/settlements/<agreement_id>/trigger/` — trigger settlement |
| **Notification** | `GET /api/notifications/<agreement_id>/` — list events |
| **Payments** | `POST /api/payments/link/` — generate payment link |
| **Webhooks** | `POST /webhooks/intasend/`, `/webhooks/mpesa/`, `/webhooks/stripe/` |

---

## Agreement Flow

```
CREATED → PAYMENT_PENDING → COLLECTED → WAITING → READY → SETTLING → SETTLED
                                                              ↘ REFUNDED
                                                    CANCELLED at any point
```

**Immediate split** (no conditions): `CREATED → PAYMENT_PENDING → COLLECTED → READY → SETTLING → SETTLED`

---

## Platform Fee

Every agreement auto-includes a 5% platform fee to `+254715641339` (IntaSend payout). Configurable via env vars:
- `TRUSTLAYER_PLATFORM_FEE_PERCENT=5.00`
- `TRUSTLAYER_PLATFORM_PHONE=+254715641339`

---

## Quick Start

```bash
cp .env.example .env
docker compose up -d
docker exec trustlayer_api python manage.py migrate
```

## Live

`https://miranda-stockish-spacially.ngrok-free.dev` — all API calls must include header `ngrok-skip-browser-warning: true`.

---

<p align="center">
  <sub>Built for Africa. Safe payments. Real trust.</sub>
</p>
