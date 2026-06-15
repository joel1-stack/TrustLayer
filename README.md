# TrustLayer

**Escrow infrastructure for African digital commerce.**

M-Pesa moves money. TrustLayer controls *when* it moves.

## The Problem

| Issue | Reality |
|---|---|
| Buyer pays → seller disappears | No enforcement |
| Disputes take months | Courts are too slow |
| Marketplaces take no responsibility | Zero protection |

## The Solution

```
PENDING → HELD → DELIVERED → RELEASED
    ↓         ↓
REFUNDED   DISPUTED → RESOLVED
```

Funds are held conditionally until delivery is confirmed or disputes are resolved.

- 48h dispute SLA
- Escrow-based payment flow
- Bad-faith dispute penalties

## API Protocol — SMS-first, API-only

TrustLayer is a **pure API protocol** with no website, dashboard, or checkout page. The primary interface is SMS; browser is a fallback. Integrate via REST API endpoints.

### API Endpoints

#### Merchants
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/merchants/register/` | Register a merchant |
| POST | `/api/v1/merchants/login/` | Authenticate a merchant |
| GET/PUT | `/api/v1/merchants/profile/` | Get/update profile |
| POST | `/api/v1/merchants/keys/regenerate/` | Regenerate API keys |

#### Sessions (JWT)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/sessions/create/` | Create a session |
| GET | `/api/v1/sessions/validate/<token>/` | Validate a session |
| DELETE | `/api/v1/sessions/consume/<token>/` | Consume a session |

#### Payments (M-Pesa)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/pay/initiate/` | Initiate STK Push |
| POST | `/api/v1/pay/direct-stk/` | Direct STK Push |
| POST | `/api/v1/pay/callbacks/mpesa/` | C2B callback (Safaricom) |
| POST | `/api/v1/pay/callbacks/b2c/result/` | B2C result callback |
| POST | `/api/v1/pay/callbacks/b2c/timeout/` | B2C timeout callback |

#### Escrow Deals
| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/v1/deals/` | List / create deals |
| GET | `/api/v1/deals/<code>/` | Deal status |
| POST | `/api/v1/deals/<code>/confirm/` | Buyer confirms delivery |
| POST | `/api/v1/deals/<code>/seller-deliver/` | Seller marks delivered |
| POST | `/api/v1/deals/<code>/dispute/` | Raise a dispute |

#### Disputes
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/disputes/open/` | Open a dispute |
| POST | `/api/v1/disputes/evidence/` | Submit evidence |
| GET | `/api/v1/disputes/status/<id>/` | Dispute status |
| POST | `/api/v1/disputes/admin/resolve/` | Admin resolve |

#### Webhooks
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/webhooks/register/` | Register webhook |
| GET | `/api/v1/webhooks/list/` | List webhooks |
| DELETE | `/api/v1/webhooks/delete/<id>/` | Delete webhook |
| GET | `/api/v1/webhooks/logs/<id>/` | Delivery logs |

#### Trust Scoring
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/trust/my-score/` | My trust score |
| GET | `/api/v1/trust/merchant/<key>/` | Public trust score |

## Tech Stack

- Python 3.12 + Django / DRF
- PostgreSQL 16 (Alpine)
- Redis 7 (Alpine) — cache & Celery broker
- Celery — async tasks & scheduled jobs
- Docker Compose — 5 services
- M-Pesa Daraja API (C2B STK Push + B2C payout)

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd trustlayer

# 2. Environment variables
cp .env.example .env
# Edit .env with your M-Pesa sandbox credentials

# 3. Build and launch
docker compose up -d --build

# 4. Create admin user
docker compose exec django_api python manage.py createsuperuser

# 5. Verify
curl http://localhost:8000/api/v1/merchants/register/
```

### Services

| Service | Container | Port | Role |
|---|---|---|---|
| `postgres_db` | `trustlayer_db` | 5432 | Primary database |
| `redis_cache` | `trustlayer_redis` | 6379 | Cache & message broker |
| `django_api` | `trustlayer_api` | 8000 | API server |
| `celery_worker` | `trustlayer_worker` | — | Async task worker |
| `celery_beat` | `trustlayer_beat` | — | Scheduled tasks |

### M-Pesa Sandbox Testing

1. Start ngrok: `ngrok http 8000`
2. Update `.env`:
   ```
   MPESA_CALLBACK_URL=https://<ngrok-id>.ngrok.io/api/v1/pay/callbacks/mpesa/
   MPESA_B2C_RESULT_URL=https://<ngrok-id>.ngrok.io/api/v1/pay/callbacks/b2c/result/
   MPESA_B2C_TIMEOUT_URL=https://<ngrok-id>.ngrok.io/api/v1/pay/callbacks/b2c/timeout/
   ```
3. Restart API: `docker compose restart django_api`

## Domain Architecture

```
backend/
├── apps/
│   ├── merchants/      # Registration, auth, API keys
│   ├── payments/       # M-Pesa STK Push + B2C
│   ├── escrow/         # Deal lifecycle (state machine)
│   ├── disputes/       # Dispute resolution
│   ├── webhooks/       # Merchant webhook delivery
│   ├── notifications/  # SMS (Africa's Talking)
│   ├── trust_scoring/  # Trust scoring system
│   └── compliance/     # KYC / compliance
├── trustlayer/         # Django project config
├── templates/legal/    # Terms & dispute policy
└── Dockerfile
```

## License

MIT
