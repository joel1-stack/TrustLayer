# TrustLayer v1 — DEPLOYMENT READY ✅

**Built:** September 15, 2026  
**Status:** All core pages complete, dark mode with orange accents, ready for demo

---

## 🎨 Design System

### Color Palette (From Mobile Screenshots)
- **Background:** `#0B0F19` — Deep slate (not pure black)
- **Surface:** `#1E293B` — Midnight grey (cards, panels)
- **Primary Action:** `#F97316` — Vibrant orange (buttons, status badges, rays)
- **Text Main:** `#F8FAFC` — Pure white (headings, case IDs)
- **Text Muted:** `#94A3B8` — Cool grey (descriptions, timestamps)
- **Border:** `#334155` — Steel grey (subtle lines)
- **Success:** `#10B981` — Emerald green (resolved status)
- **Danger:** `#EF4444` — Red (escalated, high priority)

### Visual Features
- **Orange Rays:** Radial gradient effect from top center (20% opacity)
- **S-Curve Footer:** Wave with orange glow on bottom curve
- **Cards:** Floating panels with rounded corners (12px radius)
- **Typography:** Inter font, high contrast

---

## 📄 Pages Built

### Customer Pages

1. **landing.html** (`/`)
   - Hero section with 64px heading
   - Orange highlighted text
   - 4 stats cards (response time, resolution rate, cases, availability)
   - 3 flow cards with hover effects (Report → Track → Verify)
   - Bottom CTA section
   - Background image overlay from `/static/images/hero-bg.png`

2. **report.html** (`/report/`)
   - Problem type radio buttons (transaction dispute, payment, account, other)
   - Transaction details form (ref, amount, currency, date)
   - Description textarea
   - File upload with preview
   - Contact information fields
   - Dark styled inputs with orange focus states

3. **case_detail.html** (`/case/{case_id}/`)
   - Case header with ID and status badge
   - 2-column layout:
     - **Left:** Timeline with dots + connecting lines, customer/agent messages
     - **Right:** Case details (info rows), evidence cards, verification CTA
   - Add message form

4. **verify.html** (`/case/{case_id}/verify/`)
   - Centered card with check icon
   - Case ID badge
   - Resolution details box (orange left border)
   - Large YES (green) and NO (red) buttons with icons
   - Hover effects with scale and shadow
   - Footer with return link

5. **track.html** (`/track/`)
   - Case ID search input
   - Redirects to case_detail

6. **report_success.html** (after form submission)
   - Success message with case ID
   - Link to track case

7. **case_not_found.html** (404 for cases)
   - Error message
   - Return to home

### Agent Pages

8. **agent_dashboard.html** (`/admin/`)
   - Header with sign out button
   - 4 stat cards (active cases, avg response, resolved today, success rate)
   - Filters bar (status, priority, type dropdowns)
   - Case queue table with:
     - Case ID (clickable)
     - Customer name
     - Problem type
     - Priority badge
     - Status badge
     - Created date
     - Open button

9. **agent_case.html** (`/admin/case/{case_id}/`)
   - Breadcrumb navigation
   - Large case header with meta fields (customer, contact, transaction, amount, priority)
   - 2-column layout:
     - **Left:** Customer statement, investigation notes list + add note form, resolution form
     - **Right:** Quick actions, evidence list, compact timeline
   - Resolution form with 4 radio options:
     - Confirmed fraud
     - Transaction legitimate
     - Customer error
     - Unable to determine
   - Resolution details textarea
   - Submit/Escalate/Cancel buttons

---

## 🗄️ Database Schema

### Case Model
```python
class Case(models.Model):
    case_id              # CASE-XXXXX (unique)
    status               # OPEN, INVESTIGATING, RESOLVED, etc.
    status_code_value    # 10000, 20000, 30000...
    problem_type         # TRANSACTION_DISPUTE, PAYMENT_ISSUE, ACCOUNT_ISSUE
    txn_id               # Transaction reference
    amount               # Decimal
    currency             # KES, USD, EUR
    description          # Customer statement
    date_occurred        # Date
    customer_name
    customer_email
    customer_phone
    assigned_team        # FRAUD_OPERATIONS
    priority             # LOW, NORMAL, HIGH, CRITICAL
    investigation_notes
    finding
    resolution_type
    resolution_note
    resolved_by
    customer_verified    # Boolean
    verification_note
    metadata             # JSON
    created_at
    updated_at
```

### Related Models
- **CaseMessage:** sender, sender_type (customer/agent), text
- **CaseEvidence:** evidence_type, url, filename, description
- **CaseTimeline:** from_status, to_status, reason, triggered_by

---

## 🔗 URL Routes

### Customer Routes
```
/                           → landing.html
/report/                    → report.html
/report/submit/             → creates case, redirects to report_success.html
/case/{case_id}/            → case_detail.html
/case/{case_id}/verify/     → verify.html
/case/{case_id}/confirm/    → processes verification, redirects to case detail
/case/{case_id}/message/    → adds message, redirects to case detail
/track/                     → track.html
```

### Agent Routes
```
/admin/                     → agent_dashboard.html
/admin/case/{case_id}/      → agent_case.html
/admin/case/{case_id}/message/  → adds agent message
```

### API Routes
```
/api/v1/                    → REST API endpoints
/api/docs/                  → Swagger UI
/api/docs/redoc/            → ReDoc
/api/docs/schema/           → OpenAPI schema
/health/                    → Health check
```

---

## 🚀 Running the System

### Prerequisites
- Docker & Docker Compose
- ngrok (for external access)

### Start Services
```bash
cd backend-project
docker-compose up -d
```

### Services Running
- **PostgreSQL:** `localhost:5432`
- **Redis:** `localhost:6379`
- **Django API:** `localhost:8000`
- **Celery Worker:** Background tasks
- **Celery Beat:** Scheduled tasks

### ngrok Tunnel
```bash
ngrok http 8000
```

**Current URL:** `https://miranda-stockish-spacially.ngrok-free.dev`

### Run Migrations
```bash
docker exec -it trustlayer_api python manage.py migrate
```

### Collect Static Files
```bash
docker exec -it trustlayer_api python manage.py collectstatic --noinput
```

### Create Test Data
```bash
docker exec -it trustlayer_api python create_test_cases.py
```

---

## 📊 Test Cases Created

1. **CASE-9921** — Transaction Dispute
   - Amount: KES 50,000
   - Priority: HIGH
   - Status: INVESTIGATING
   - Customer: John Doe (+254712345678)
   - Problem: "I did not make this payment"

2. **CASE-9920** — Payment Issue
   - Amount: KES 15,000
   - Priority: NORMAL
   - Status: INVESTIGATING
   - Customer: Jane Smith (jane.smith@example.com)
   - Problem: "Payment deducted twice"

3. **CASE-9919** — Account Security
   - Amount: KES 0
   - Priority: CRITICAL
   - Status: ESCALATED
   - Customer: Peter Kamau (+254700123456)
   - Problem: "Unauthorized login attempts"

---

## 🎯 The Complete Flow

```
CUSTOMER REPORTS
      ↓
   CASE CREATED (OPEN)
      ↓
EVIDENCE GATHERED
      ↓
CASE STRUCTURED
      ↓
ROUTED TO TEAM (INVESTIGATING)
      ↓
AGENT INVESTIGATES
      ↓
RESOLUTION RECORDED
      ↓
SENT FOR VERIFICATION (VERIFYING)
      ↓
CUSTOMER CONFIRMS
      ↓
  YES → RESOLVED → CLOSED
  NO  → REOPENED → INVESTIGATING
```

---

## ✅ Status Badges

| Status | Color | Badge Class |
|--------|-------|-------------|
| OPEN | Orange | `badge-open` |
| EVIDENCE_COLLECTION | Amber | `badge-evidence` |
| INVESTIGATING | Blue | `badge-investigating` |
| RESOLUTION_RECORDED | Purple | `badge-resolution` |
| ESCALATED | Red | `badge-escalated` |
| VERIFYING | Orange | `badge-verifying` |
| RESOLVED | Green | `badge-resolved` |
| REOPENED | Red | `badge-reopened` |
| CLOSED | Grey | `badge-closed` |

---

## 🔧 Configuration

### Environment Variables
- `DEBUG=True` (local dev)
- `SECRET_KEY` (Django secret)
- `DATABASE_URL` or individual DB vars
- `REDIS_URL`
- `TRUSTLAYER_BASE_URL=https://miranda-stockish-spacially.ngrok-free.dev`
- `ALLOWED_HOSTS=*` (for ngrok)
- `CSRF_TRUSTED_ORIGINS=https://miranda-stockish-spacially.ngrok-free.dev`

### Static Files
- Location: `backend/static/`
- Collected to: `backend/staticfiles/`
- Images: `backend/static/images/hero-bg.png`

---

## 📝 What's Not in v1

We explicitly excluded these to ship clean:
- ❌ Mobile app (Flutter code exists but not needed)
- ❌ KCB integration
- ❌ Safaricom M-Pesa integration
- ❌ GSMA Open Gateway
- ❌ AI agent features
- ❌ MCP server
- ❌ Five organizations multi-tenancy
- ❌ Complex trust scoring
- ❌ Voice/phone system
- ❌ Escrow/payment holding
- ❌ Ledger/settlements

**v1 Focus:** One customer problem → evidence → right person → resolution → verified outcome

---

## 🎨 Design Matches

The web UI matches the mobile screenshots you provided:
- Dark mode with orange accents ✅
- Operations dashboard stat cards ✅
- Case list with status badges ✅
- Clean, high-contrast typography ✅
- Orange "rays" glow effect ✅
- S-curve footer with glow ✅

---

## 🚢 Ready to Demo

**View the live site:**
👉 https://miranda-stockish-spacially.ngrok-free.dev/

**Test the flow:**
1. Visit landing page
2. Click "Report a Problem"
3. Fill form and submit
4. Track case with case ID
5. Agent opens `/admin/` to see queue
6. Agent clicks case → investigates → resolves
7. Customer verifies resolution

**Status:** ✅ All pages responsive, dark theme applied, ready for presentation

---

Built with the exact color palette and visual design from your mobile screenshots.
