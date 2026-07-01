<p align="center">
  <img src="https://img.icons8.com/fluency/96/shield.png" width="64"/>
</p>

<h1 align="center">TrustLayer</h1>

<p align="center">
  <b>Conditional‑release escrow for African commerce.</b><br>
  Hold funds. Confirm delivery. Release on trust.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-2ea043?logo=python">
  <img src="https://img.shields.io/badge/django-4.2-0c4b33?logo=django">
  <img src="https://img.shields.io/badge/celery-✅-3fb950">
  <img src="https://img.shields.io/badge/M--Pesa-integrated-00a859">
</p>

---

### What it does

TrustLayer lets businesses accept customer payments into **conditional escrow**.  
Money is held until the buyer confirms delivery — then it's released to the seller.

| Problem | TrustLayer |
|---|---|
| Customers pay, goods never arrive | Funds held in escrow |
| Seller delivers, buyer ghosts | Auto‑release after confirmation |
| Chargebacks, disputes, refunds | Built‑in dispute workflow |
| Bank integrations for Africa | M‑Pesa STK Push & B2C out‑of‑box |

---

### Quick start

**Live:** [https://miranda-stockish-spacially.ngrok-free.dev](https://miranda-stockish-spacially.ngrok-free.dev) — register your business, dashboard loads with live stats.

**Local:**
```bash
cp .env.example .env
docker compose up -d
```

---

### Portal (business owner)

Every business starts here:

| Endpoint | What it does |
|---|---|
| `GET /` | Landing page (register / sign in) |
| `POST /register/` | Create merchant account → get API keys |
| `POST /login/` | Sign in (session‑based) |
| `GET /portal/dashboard/` | Business dashboard with live stats |
| `GET /api/stats/` | Revenue, pending, settled, fees |
| `GET /api/proxy/deals/` | Your transactions (session auth) |
| `POST /api/proxy/collect/` | Send STK Push (session auth) |
| `POST /api/proxy/withdraw/` | Withdraw to M‑Pesa (session auth) |

---

### API — Payment & Escrow

```http
Authorization: Bearer <api_key>
```

| Method | Endpoint | What it does |
|---|---|---|
| **POST** | `/api/v1/pay/initiate/` | Create deal + send STK Push |
| **POST** | `/api/v1/pay/direct-stk/` | Fire STK Push directly (no checkout link) |
| **POST** | `/api/v1/pay/flow/collect/` | Collect payment (IntaSend flow) |
| **POST** | `/api/v1/pay/flow/payout/` | Send payout (IntaSend flow) |
| **GET** | `/api/v1/pay/flow/wallet/` | Check wallet balance (IntaSend) |
| **POST** | `/api/v1/pay/flow/full/` | Full collect → hold → release flow |
| **GET** | `/api/v1/deals/` | List your deals |
| **GET** | `/api/v1/deals/<code>/` | Deal status |
| **POST** | `/api/v1/deals/<code>/confirm/` | Buyer confirms delivery |
| **POST** | `/api/v1/deals/<code>/seller-deliver/` | Seller marks delivered |
| **POST** | `/api/v1/deals/<code>/dispute/` | Raise a dispute |
| **POST** | `/api/v1/pay/callbacks/mpesa/` | M‑Pesa STK callback receiver |
| **POST** | `/api/v1/pay/callbacks/b2c/result/` | M‑Pesa B2C result receiver |

---

### API — Merchant & Ledger

| Method | Endpoint | What it does |
|---|---|---|
| **POST** | `/api/v1/merchants/register/` | Create merchant (API) |
| **POST** | `/api/v1/merchants/login/` | Auth (returns session token) |
| **GET** | `/api/v1/merchants/profile/` | Your merchant profile |
| **POST** | `/api/v1/merchants/keys/regenerate/` | Rotate API keys |
| **GET** | `/api/v1/ledger/stats/` | Ledger summary |
| **GET** | `/api/v1/ledger/wallet/<phone>/` | Wallet balance |
| **POST** | `/api/v1/settle/queue/` | Queue a withdrawal |
| **POST** | `/api/v1/settle/process/` | Trigger settlement |

---

### API — Webhooks & Trust

| Method | Endpoint | What it does |
|---|---|---|
| **POST** | `/api/v1/webhooks/register/` | Register a webhook URL |
| **GET** | `/api/v1/webhooks/list/` | Your webhooks |
| **POST** | `/api/v1/webhooks/delete/<id>/` | Delete a webhook |
| **GET** | `/api/v1/trust/my-score/` | Your trust score |
| **GET** | `/api/v1/trust/merchant/<key>/` | Public trust score |
| **POST** | `/api/v1/disputes/open/` | Open a dispute |
| **POST** | `/api/v1/disputes/evidence/` | Submit evidence |
| **GET** | `/api/v1/disputes/status/<id>/` | Dispute status |

---

### Architecture

```
         ┌──────────┐      ┌──────────────┐
Customer │  M‑Pesa  │◄────►│  TrustLayer   │
  phone  │  STK/B2C │      │  API + Celery │
         └──────────┘      └──────┬───────┘
                                  │
                         ┌────────▼────────┐
                         │  PostgreSQL      │
                         │  + Redis (cache) │
                         └─────────────────┘
```

---

<p align="center">
  <sub>Built for Africa. Safe payments. Real trust.</sub>
</p>
