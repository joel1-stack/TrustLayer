<h1 align="center">TrustLayer</h1>

<p align="center">
  <b>The resolution infrastructure that turns a customer's money problem<br>into a verified, auditable outcome.</b><br><br>
  Report → Evidence → Route → Investigate → Resolve → Verify
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-2ea043?logo=python">
  <img src="https://img.shields.io/badge/django-4.2-0c4b33?logo=django">
  <img src="https://img.shields.io/badge/postgresql-16-336791?logo=postgresql">
  <img src="https://img.shields.io/badge/license-MIT-blue">
</p>

---

## What is TrustLayer?

TrustLayer is the **customer-facing resolution loop**. Not a bank ledger. Not a support ticket. Not a CRM. A single loop that closes.

```
CUSTOMER                    ORGANIZATION
   │                            │
   ▼                            ▼
┌───────────────── TRUSTLAYER ─────────────────┐
│                                              │
│  1. INTAKE      "Report your problem"        │
│        ↓                                     │
│  2. CASE        One case, one ID, one record │
│        ↓                                     │
│  3. EVIDENCE    Auto-checked completeness    │
│        ↓                                     │
│  4. ROUTING     Right team, right priority   │
│        ↓                                     │
│  5. WORKSPACE   Agent sees everything        │
│        ↓                                     │
│  6. RESOLUTION  Structured outcome recorded  │
│        ↓                                     │
│  7. VERIFICATION "Did we actually fix it?"   │
│        ↓                                     │
│  8. AUDIT       Every step, permanently      │
│                                              │
└──────────────────────────────────────────────┘
```

**TrustLayer does not decide whether the customer deserves their money back. It makes the organization's decision and resolution process structured, traceable, and verifiable.**

---

## The Lifecycle

```
    ┌──────────────────────────────────────────────────────────┐
    │                  TRUSTLAYER CASE LOOP                     │
    │                                                           │
    │  1. CREATE ──→ OPEN                                      │
    │       │                                                   │
    │       ▼                                                   │
    │  2. EVIDENCE ──→ EVIDENCE_COLLECTION                     │
    │       │                                                   │
    │       ▼                                                   │
    │  3. INVESTIGATE ──→ INVESTIGATING                        │
    │       │                                                   │
    │       ▼                                                   │
    │  4. RESOLVE ──→ RESOLUTION_RECORDED                      │
    │       │                                                   │
    │       ▼                                                   │
    │  5. VERIFY ──→ VERIFYING                                 │
    │       │                                                   │
    │   ┌───┴───┐                                               │
    │   ▼       ▼                                               │
    │  YES      NO                                              │
    │   │       │                                               │
    │   ▼       ▼                                               │
    │ RESOLVED  REOPENED ──→ back to INVESTIGATING             │
    │   │                                                       │
    │   ▼                                                       │
    │ CLOSED (immutable record)                                 │
    └──────────────────────────────────────────────────────────┘
```

---

## Live Demo

| URL | Description |
|-----|-------------|
| [miranda-stockish-spacially.ngrok-free.dev](https://miranda-stockish-spacially.ngrok-free.dev) | Customer portal |
| [miranda-stockish-spacially.ngrok-free.dev/api/docs/](https://miranda-stockish-spacially.ngrok-free.dev/api/docs/) | API documentation (Swagger) |
| [miranda-stockish-spacially.ngrok-free.dev/health/](https://miranda-stockish-spacially.ngrok-free.dev/health/) | Health check |

### Pages

| Page | URL | Who |
|------|-----|-----|
| Landing | `/` | Customer |
| Report a Problem | `/report/` | Customer |
| Track a Case | `/track/` | Customer |
| Case Detail | `/case/{CASE-ID}/` | Customer |
| Verify Resolution | `/case/{CASE-ID}/verify/` | Customer |
| How It Works | `/how-it-works/` | Anyone |
| Features | `/features/` | Anyone |
| About | `/about/` | Anyone |
| Agent Login | `/agent/login/` | Agent |
| Agent Dashboard | `/agent/` | Agent |
| Agent Case Workspace | `/agent/case/{CASE-ID}/` | Agent |
| API Documentation | `/api/docs/` | Developer |

**Agent credentials:** `joelkaunda15` / `wherby`

---

## API Reference

Base: `https://miranda-stockish-spacially.ngrok-free.dev/api/v1`

| Method | Endpoint | Description | Step |
|--------|----------|-------------|------|
| `POST` | `/cases/create/` | Create a new case | 1. Report |
| `GET` | `/cases/` | List all cases | — |
| `GET` | `/cases/{id}/` | Full case detail + timeline + messages + evidence | — |
| `POST` | `/cases/{id}/evidence/` | Add evidence to case | 2. Evidence |
| `POST` | `/cases/{id}/investigate/` | Agent starts investigation | 3. Investigate |
| `POST` | `/cases/{id}/resolve/` | Record resolution outcome | 4. Resolve |
| `POST` | `/cases/{id}/verify/` | Send resolution to customer | 5. Verify |
| `POST` | `/cases/{id}/confirm/` | Customer confirms/rejects | 5b. Confirm |
| `POST` | `/cases/{id}/close/` | Close resolved case | 6. Close |
| `POST` | `/cases/{id}/messages/` | Add message to case thread | — |

### Example: Create a Case

```bash
curl -X POST https://miranda-stockish-spacially.ngrok-free.dev/api/v1/cases/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "problem_type": "TRANSACTION_DISPUTE",
    "txn_id": "TXN-8839201",
    "amount": 50000,
    "currency": "KES",
    "description": "I did not make this payment. Someone accessed my account.",
    "customer_name": "Jane Doe",
    "customer_email": "jane@example.com",
    "customer_phone": "+254712345678"
  }'
```

Response:
```json
{
  "case_id": "CASE4DRUHSCT4F",
  "status": "OPEN",
  "message": "Case CASE4DRUHSCT4F created."
}
```

### Problem Types

| Value | Label |
|-------|-------|
| `TRANSACTION_DISPUTE` | I don't recognize a transaction |
| `PAYMENT_PROBLEM` | Payment problem |
| `ACCOUNT_PROBLEM` | Account security issue |
| `OTHER` | Other |

### Resolution Types

| Value | Label |
|-------|-------|
| `CONFIRMED_FRAUD` | Confirmed fraud |
| `TRANSACTION_LEGITIMATE` | Transaction legitimate |
| `CUSTOMER_ERROR` | Customer error |
| `UNABLE_TO_DETERMINE` | Unable to determine |
| `REFUNDED` | Refund initiated |

---

## What TrustLayer Does NOT Do

| Not TrustLayer | Why |
|----------------|-----|
| Does not hold or move money | No custody risk, no license needed |
| Does not decide fraud | The organization owns the decision |
| Does not replace core banking, CRM, or M-Pesa | It sits between the customer and those systems |
| Does not fight chargebacks | Different side — customer recourse, not merchant defense |
| Does not sell AI transformation | It's a product with a boundary, not a services firm |

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Django + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| API Docs | drf-spectacular (Swagger / ReDoc) |
| Containerization | Docker + Docker Compose |
| Tunnel | ngrok |

---

## Project Structure

```
backend/
├── manage.py
├── apps/
│   ├── core/              # Constants, state machine definitions
│   ├── agreements/        # Case, CaseMessage, CaseEvidence, CaseTimeline models
│   ├── state_machine/     # State transition logic
│   └── api_v1/            # REST API views and URLs
├── templates/             # Django templates (all pages)
│   ├── base.html          # Design system: dark mode, orange accent
│   ├── landing.html       # Customer landing page
│   ├── report.html        # Intake form
│   ├── case_detail.html   # Customer case view
│   ├── verify.html        # Resolution verification
│   ├── agent_login.html   # Agent authentication
│   ├── agent_dashboard.html  # Agent case queue
│   ├── agent_case.html    # Agent workspace
│   ├── how_it_works.html  # Product explanation
│   ├── features.html      # Feature list
│   └── about.html         # Company info
├── trustlayer/
│   ├── settings.py        # Django configuration
│   └── urls.py            # Root URL routing
├── media/evidence/        # Uploaded evidence files
└── static/                # Static assets
```

---

## Run Locally

```bash
# Start all services
docker compose up --build

# App runs at http://localhost:8000
# API docs at http://localhost:8000/api/docs/
```

### Database

Django migrations run automatically on startup. To reset:

```bash
docker exec trustlayer_db psql -U trustlayer -d trustlayer -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec trustlayer_api python manage.py makemigrations
docker exec trustlayer_api python manage.py migrate
```

---

## The Market

- **The regulator:** CBK's 2025–2028 financial inclusion strategy targets stronger digital complaint management and full implementation of e-money consumer-protection measures by 2026.
- **The budget:** Banks are paying KSh 250K/month for manual chargeback analysts. TrustLayer replaces the workflow, not the person.
- **The gap:** M-Pesa exposes transaction and reversal capabilities through Daraja, but TrustLayer is aimed at the broader customer-dispute workflow: intake, evidence, investigation, communication, resolution tracking and verification.

> **TrustLayer makes verified resolution the product's center**, rather than treating it as a side feature of CRM, helpdesk, payments or fraud software.

---

## License

MIT
