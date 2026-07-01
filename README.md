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

```bash
cp .env.example .env        # configure your keys
docker compose up -d        # starts API + DB + Redis + workers
```

Open **http://localhost:8000** → register your business → dashboard loads with live stats.

---

### API endpoints

| Endpoint | What it does |
|---|---|
| `POST /register/` | Create merchant account (returns API key) |
| `POST /login/` | Sign in (session‑based dashboard) |
| `GET /api/stats/` | Revenue, pending, settled, fees |
| `POST /api/v1/pay/flow/collect/` | STK Push to customer phone |
| `POST /api/v1/deals/` | Create an escrow deal |
| `GET /api/v1/deals/` | List your deals |
| `POST /api/v1/settle/queue/` | Withdraw to M‑Pesa |
| `POST /api/v1/webhooks/mpesa/` | M‑Pesa callback receiver |

Dashboard proxies (`/api/proxy/*`) are available when logged in via the portal — no API key needed.

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
