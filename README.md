# TrustLayer

**Escrow orchestration backend for safe P2P payments in Kenya.**

TrustLayer is a modular monolith that handles conditional payments using M-Pesa Daraja. It acts as a **trust layer** between buyer and seller — never holding funds long-term, only orchestrating state and release logic.

### Core Features
- M-Pesa STK Push + idempotent webhook handling
- Escrow state machine (Pending → Initiated → Held → Released/Refunded/Disputed)
- Deal-code based flow (no buyer login required)
- Multi-provider ready (M-Pesa live, Pesapal and bank adapters prepared)
- Dockerized setup with PostgreSQL + Redis + Celery
- Audit logging and basic retry queue for reliability

### Architecture
Modular monolith built with clear boundaries:
- **Escrow Module** — state machine and business logic (provider-agnostic)
- **Payment Gateway Module** — adapter pattern for multiple providers
- **Webhook Normalizer + DLQ** — unified handling with retry logic
- **Trust & Notification Modules** — scoring and SMS

Designed for easy evolution: manual B2C in MVP → PSP partnership → formal bank custody.

### Tech Stack
- Python + Django REST Framework
- PostgreSQL (ACID transactions)
- Redis + Celery (caching, tasks, retry queue)
- Docker + docker-compose
- M-Pesa Daraja API

### Status
- Working M-Pesa integration with live STK Push and callbacks
- Modular structure locked
- Moving toward first real user tests

### Next Steps
- Complete 5-user validation flow
- Add Pesapal adapter
- Prepare for PSP partnership and CBK sandbox path

Built with focus on simplicity, reliability, and real Kenyan P2P needs.

---

**TrustLayer** — Safe payments. Real trust.
