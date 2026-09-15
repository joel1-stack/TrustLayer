# TrustLayer v1 — Endpoint Testing Guide

## Customer Flow (Browser 1)

### 1. Landing Page
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/
**Expected:** Hero with dark section, white background, stats, 3 flow cards
**Test:** Click "Report a Problem" button

### 2. Report Form
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/report/
**Expected:** Form with problem type radios, transaction fields, evidence upload
**Test:** 
- Select "I don't recognize a transaction"
- Enter: TXN-TEST-001, 25000, KES
- Description: "Unauthorized charge on my account"
- Submit

### 3. Report Success
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/report/submit/
**Expected:** Success message with case ID
**Test:** Note the CASE-XXXXX ID, click "Track Case"

### 4. Track Case
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/track/
**Expected:** Search input for case ID
**Test:** Enter your case ID, click search

### 5. Case Detail (Customer View)
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/case/CASE-XXXXX/
**Expected:** Timeline, messages, evidence, case info sidebar
**Test:** 
- View timeline events
- Add a message
- Check if verification CTA appears (only when status = VERIFYING)

### 6. Verification
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/case/CASE-XXXXX/verify/
**Expected:** YES/NO buttons, resolution details
**Test:** Click "YES, IT'S RESOLVED" or "NO, STILL A PROBLEM"

---

## Agent Flow (Browser 2)

### 7. Agent Dashboard
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/admin/
**Expected:** Stats cards, filters, case queue table
**Test:** 
- See 4 stat cards (active cases, avg response, resolved today, success rate)
- Filter by status
- Click "Open" button on a case

### 8. Agent Case Detail
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/admin/case/CASE-XXXXX/
**Expected:** Full case with investigation notes, resolution form
**Test:**
- Add investigation note
- Select resolution type (Confirmed Fraud)
- Enter resolution note
- Click "Submit Resolution"

### 9. Agent Add Message
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/admin/case/CASE-XXXXX/message/
**Expected:** Message added to case, redirect back to case
**Test:** Add message as agent

---

## API Endpoints

### 10. Health Check
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/health/
**Expected:** `{"status": "ok"}`

### 11. API Swagger Docs
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/api/docs/
**Expected:** Interactive API documentation

### 12. API ReDoc
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/api/docs/redoc/
**Expected:** Alternative API documentation

---

## Error Pages

### 13. Case Not Found
**URL:** https://miranda-stockish-spacially.ngrok-free.dev/case/INVALID-ID/
**Expected:** "Case not found" message with return link

---

## Complete Flow Test

1. **Customer:** Go to `/` → Click "Report a Problem"
2. **Customer:** Fill form → Submit → Note CASE-ID
3. **Agent:** Go to `/admin/` → See new case in queue
4. **Agent:** Click "Open" → View case details
5. **Agent:** Add investigation note → Submit
6. **Agent:** Select "Confirmed Fraud" → Add resolution note → Submit
7. **System:** Case status changes to RESOLUTION_RECORDED
8. **Customer:** Go to `/case/CASE-ID/` → See resolution
9. **Customer:** Click "Verify Resolution" → Click "YES, IT'S RESOLVED"
10. **System:** Case status changes to RESOLVED → CLOSED

**Success:** Case goes from OPEN → INVESTIGATING → RESOLUTION_RECORDED → VERIFYING → RESOLVED → CLOSED

---

## Quick Test Commands

```bash
# Test homepage
curl https://miranda-stockish-spacially.ngrok-free.dev/

# Test health
curl https://miranda-stockish-spacially.ngrok-free.dev/health/

# Test API docs
curl https://miranda-stockish-spacially.ngrok-free.dev/api/docs/

# Create test case via Docker
docker exec -it trustlayer_api python create_test_cases.py
```

---

## Expected Status Flow

```
OPEN
  ↓
EVIDENCE_COLLECTION (optional)
  ↓
INVESTIGATING
  ↓
RESOLUTION_RECORDED
  ↓
VERIFYING
  ↓
RESOLVED
  ↓
CLOSED

OR (if customer says NO):

VERIFYING
  ↓
REOPENED
  ↓
INVESTIGATING (loop back)
```
