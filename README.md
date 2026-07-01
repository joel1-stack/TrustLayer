# TrustLayer

**Escrow infrastructure for African digital commerce.**

M-Pesa moves money. TrustLayer controls *when* it moves.

## The 6 Modules

```
┌──────────────────────────────────────────────────────┐
│                   TRUSTLAYER ENGINE                   │
├──────────┬────────┬────────┬────────┬────────┬───────┤
│ IDENTITY │PAYMENTS│ LEDGER  │SETTLE  │ TRUST  │ OBSERV│
│          │        │        │ MENT   │        │ ABILITY│
├──────────┼────────┼────────┼────────┼────────┼───────┤
│ Portal   │IntaSend│ Double │ Payout │ Escrow │ Stats │
│ Register │ M-Pesa │-Entry  │ Queue  │ State  │ Dash- │
│ Login    │ STK    │ Accnts │ B2C    │ Mach.  │ board │
│ Roles    │ Card   │ Journl │ Bank   │ Disp-  │       │
│          │        │ Wallet │ Transf │ ute    │       │
└──────────┴────────┴────────┴────────┴────────┴───────┘
```

Every customer payment flows through all 6 modules automatically:

```
Customer pays KES 1,000
  → IntaSend / M-Pesa collects
  → Webhook fires → Ledger records (DEBIT/CREDIT)
  → Escrow holds funds
  → Buyer confirms delivery
  → Split engine fires (95% merchant, 5% platform)
  → Settlement queues B2C payout
  → Merchant receives money
  → Dashboard updates instantly
```

## Flow (End-to-End)

```
PENDING  →  HELD  →  DELIVERED  →  RELEASED  →  SETTLED
    ↓          ↓
 REFUNDED   DISPUTED  →  RESOLVED
```

## API Endpoints

### Module 1: Identity (Portal + Merchants)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Portal landing page |
| POST | `/register/` | Register merchant (with payout fields) |
| POST | `/login/` | Login with email + password |
| GET | `/portal/dashboard/` | Merchant dashboard |
| GET/PUT | `/api/v1/merchants/profile/` | Get/update profile |

### Module 2: Payments (IntaSend + M-Pesa)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pay/flow/wallet/` | IntaSend wallet balance |
| POST | `/api/v1/pay/flow/collect/` | Send STK Push to buyer |
| POST | `/api/v1/pay/flow/payout/` | Send B2C payout to merchant |
| POST | `/api/v1/pay/flow/full/` | Full A-Z flow (collect → hold → payout) |
| POST | `/api/v1/pay/webhooks/intasend/` | IntaSend callback webhook |
| POST | `/api/v1/pay/initiate/` | Initiate M-Pesa STK Push |
| POST | `/api/v1/pay/callbacks/mpesa/` | M-Pesa C2B callback |
| POST | `/api/v1/pay/callbacks/b2c/result/` | B2C result callback |

### Module 3: Ledger (Double-Entry)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ledger/stats/` | Dashboard stats (float, fees, escrow) |
| GET | `/api/v1/ledger/wallet/<phone>/` | Wallet balance for phone |

### Module 4: Settlement (Payouts)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/settle/queue/` | Queue a payout |
| POST | `/api/v1/settle/process/` | Process a queued payout |

### Module 5: Trust (Escrow + Disputes)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/deals/` | List / create deals |
| GET | `/api/v1/deals/<code>/` | Deal status |
| POST | `/api/v1/deals/<code>/confirm/` | Buyer confirms delivery |
| POST | `/api/v1/deals/<code>/seller-deliver/` | Seller marks delivered |
| POST | `/api/v1/deals/<code>/dispute/` | Raise a dispute |
| POST | `/api/v1/disputes/open/` | Open a dispute |
| POST | `/api/v1/disputes/admin/resolve/` | Admin resolve |

### Module 6: Observability (Dashboard)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/ledger/stats/` | Platform-wide stats |
| GET | `/api/v1/ledger/wallet/<phone>/` | Wallet lookup |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | Django 5.x + DRF |
| Database | PostgreSQL 16 (Alpine) |
| Cache | Redis 7 (Alpine) |
| Async Tasks | Celery |
| Container | Docker Compose (5 services) |
| Payments IN | M-Pesa Daraja (STK Push) + IntaSend |
| Payments OUT | IntaSend B2C Payouts |
| SMS | Africa's Talking |
| Tunnel | ngrok |

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd trustlayer

# 2. Environment
cp .env.example .env
# Fill in M-Pesa and IntaSend credentials

# 3. Build and launch
docker compose up -d --build

# 4. Create admin
docker compose exec django_api python manage.py createsuperuser

# 5. Verify
curl http://localhost:8000/
```

## Database Schema

```
merchants
  ├── escrow_deals         (escrow state machine)
  ├── payment_transactions (M-Pesa/IntaSend records)
  ├── ledger_accounts      (double-entry accounts)
  ├── ledger_transactions  (financial events)
  ├── ledger_journal_entries (DEBIT/CREDIT pairs)
  ├── ledger_wallets       (per-user balances)
  ├── settlement_payouts   (B2C payout queue)
  ├── settlement_bank_accounts (merchant bank details)
  ├── fee_records          (platform revenue)
  └── disputes             (dispute resolution)
```

## Architecture

```
backend/
├── apps/
│   ├── portal/          # Merchant portal (HTML + JS)
│   ├── merchants/       # Registration, auth, API keys
│   ├── payments/        # IntaSend + M-Pesa adapters
│   │   └── adapters/    # mpesa.py, intasend.py
│   ├── ledger/          # Double-entry accounting
│   ├── settlements/     # Payout queue + processing
│   ├── escrow/          # Deal lifecycle (state machine)
│   ├── disputes/        # Dispute resolution
│   ├── webhooks/        # Merchant webhook delivery
│   ├── notifications/   # SMS (Africa's Talking)
│   └── trust_scoring/   # Trust scoring system
├── trustlayer/          # Django project config
├── templates/           # HTML templates
└── Dockerfile
```

## License

MIT
