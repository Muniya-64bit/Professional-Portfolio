# KVPL — Tea Plantation Input & Resource Optimization System

Full-stack plantation management system for Kelani Valley Plantations Ltd.  
Tracks labour rotation, fertilizer schedules, water efficiency, and ROI across 4 estates.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, plain CSS |
| Backend | Python 3, Flask, Flask-CORS, PyJWT, bcrypt |
| Database | PostgreSQL 16 (Docker) |
| Auth | JWT (Bearer token) |

**Ports:** `3000` (frontend) · `5000` (backend) · `5432` (database)

---

## Prerequisites

Install these before starting:

- **Docker Desktop** — runs PostgreSQL ([docker.com](https://www.docker.com/products/docker-desktop))
- **Node.js 18+** — runs the frontend (`node -v` to check)
- **Python 3.10+** — runs the backend (`python --version` to check)
- **Git** — to clone the repo

---

## Project Structure

```
Professional-Portfolio/
├── docker-compose.yml          # PostgreSQL container
├── .env                        # Root env (Docker credentials)
│
├── backend/
│   ├── app.py                  # Flask entry point + auth routes
│   ├── auth.py                 # JWT auth helpers
│   ├── labour.py               # Labour planner API blueprint
│   ├── migrate.py              # Migration runner CLI
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Backend env (DATABASE_URL, SECRET_KEY)
│   └── migrations/
│       ├── 001_initial_schema.sql      # Tables, indexes, views
│       ├── 002_sample_data.sql         # Estates, blocks, users, base data
│       ├── 003_labour_planner_schema.sql  # Labour tables (employee, rotation, etc.)
│       ├── 004_labour_sample_data.sql  # Kundasale labour data
│       ├── 005_remaining_estates_sample_data.sql  # Ramboda, Hunasgiriya, Haputale
│       └── QUERIES.sql                 # Reference queries for all modules
│
└── frontend/
    ├── app/
    │   ├── page.jsx            # Landing page
    │   ├── dashboard/page.jsx  # Main dashboard (all tabs)
    │   ├── auth/               # Login / signup pages
    │   ├── api/apiService.js   # All API calls
    │   └── context/AuthContext.jsx  # JWT auth state
    ├── .env.local              # Frontend env (API base URL)
    └── package.json
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone <repo-url>
cd Professional-Portfolio
```

### 2. Start the database

```bash
docker-compose up -d
```

Verify it's running:

```bash
docker ps
# Should show: portfolio-db   Up
```

### 3. Set up the backend

```powershell
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate        # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

The `backend/.env` is already configured for local development:

```env
DATABASE_URL=postgresql://portfolio:portfolio_password@localhost:5432/portfolio
SECRET_KEY=frewrewvr4353v45435vv435435v34
```

> No changes needed — these match the Docker container credentials.

### 4. Run database migrations

```powershell
# Still inside backend/ with .venv active
python migrate.py migrate
```

Expected output:

```
📋 Found 5 pending migration(s):

   - 001_initial_schema.sql
   - 002_sample_data.sql
   - 003_labour_planner_schema.sql
   - 004_labour_sample_data.sql
   - 005_remaining_estates_sample_data.sql

▶️  Running: 001_initial_schema.sql
✅ Completed: 001_initial_schema.sql (205ms)
...
✅ All migrations completed successfully!
```

Check status at any time:

```powershell
python migrate.py status
```

### 5. Start the backend server

```powershell
# Inside backend/ with .venv active
python app.py
```

Backend runs at `http://localhost:5000`. You should see:

```
 * Running on http://0.0.0.0:5000
```

### 6. Set up the frontend

Open a **new terminal**:

```powershell
cd frontend

# Install dependencies
npm install

# Copy environment file (only needed once)
cp .env.local.example .env.local
```

The `.env.local` is already configured:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

### 7. Start the frontend

```powershell
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## First Login

The sample data seeds estate records, blocks, and employees but **does not include login passwords** (security). You need to create your own account first.

1. Open `http://localhost:3000`
2. Click **Get Started** or navigate to `/auth/login`
3. Click **Sign Up** and create an account with any email/password

> Password requirements: 8+ chars, uppercase, lowercase, digit, special character  
> Example: `Admin@1234`

Once signed in, you have access to all dashboard tabs including the Labour Planner.

---

## Sample Data Overview

After migrations, the database contains:

### Estates

| Estate | Region | Blocks | Workers | Rotation |
|---|---|---|---|---|
| Kundasale Estate | Central | 6 (A1–D1) | 90 | 6-round, currently Round 3 |
| Ramboda Heights | Central | 8 (E1–H2) | 96 | 8-round, currently Round 5 |
| Hunasgiriya Estate | Western | 15 (I1–M3) | 150 | 15-round, currently Round 9 |
| Haputale Park | Uva | 10 (N1–Q2) | 120 | 10-round, currently Round 4 |

### What's in each estate

- **Employees** — Named supervisors (1 per group) + pluckers (`KUN-PLK-001` style codes)
- **Worker groups** — One group per block, sized to match block capacity
- **Rotation cycle** — Full round-robin matrix so every group visits every block once per cycle
- **Labour plan** — Current week's plan with block assignments generated from rotation
- **Historical assignments** — 4 weeks of completed assignments with yield data (for productivity reports)

### Other modules

- 5 months of **fertilizer applications**, recommendations
- 5 months of **input costs** and **yield records** per estate
- **ROI snapshots** with estate rankings
- **Water usage** data with on-track/at-risk/off-track status

---

## API Reference

Base URL: `http://localhost:5000/api`

All endpoints except signup/login require:
```
Authorization: Bearer <token>
```

### Auth

| Method | Endpoint | Body |
|---|---|---|
| POST | `/auth/signup` | `{ email, password, full_name }` |
| POST | `/auth/login` | `{ email, password }` |
| GET | `/auth/profile` | — |
| POST | `/auth/refresh` | — |
| POST | `/auth/logout` | — |

### Labour Planner

| Method | Endpoint | Description |
|---|---|---|
| GET | `/labour/estates` | All estates |
| GET | `/labour/plans?estate_id=&week_start=` | List labour plans |
| POST | `/labour/plans` | Create plan + auto-generate assignments |
| GET | `/labour/plans/<id>` | Plan detail with all block assignments |
| PUT | `/labour/plans/<id>` | Update status / notes |
| PUT | `/labour/assignments/<id>` | Override group or record actual yield |
| POST | `/labour/assignments/<id>/employee-overrides` | Add/remove individual worker |
| GET | `/labour/employees?estate_id=` | List field employees |
| POST | `/labour/employees` | Add employee |
| PUT | `/labour/employees/<id>` | Update employee |
| GET | `/labour/groups?estate_id=` | List worker groups with headcount |
| POST | `/labour/groups/<id>/members` | Add/remove member from group |
| GET | `/labour/rotation?estate_id=` | Rotation cycle + full matrix |

### Quick API test with curl

```bash
# 1. Sign up
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@kvpl.com","password":"Dev@12345","full_name":"Dev User"}'

# 2. Log in (save the token)
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@kvpl.com","password":"Dev@12345"}'

# 3. List estates (replace TOKEN)
curl http://localhost:5000/api/labour/estates \
  -H "Authorization: Bearer TOKEN"

# 4. Get current week's labour plans
curl "http://localhost:5000/api/labour/plans" \
  -H "Authorization: Bearer TOKEN"

# 5. Get rotation matrix for an estate (replace ESTATE_ID)
curl "http://localhost:5000/api/labour/rotation?estate_id=ESTATE_ID" \
  -H "Authorization: Bearer TOKEN"
```

---

## Migration Reference

Migrations run in filename order. Each is tracked in `schema_migrations` and only runs once.

| File | What it does |
|---|---|
| `001_initial_schema.sql` | All tables, indexes, views, fertilizer seed data |
| `002_sample_data.sql` | 4 estates, blocks (Kundasale + Ramboda), system users, fertilizer/water/ROI data |
| `003_labour_planner_schema.sql` | New labour tables: `employee`, `worker_group`, `rotation_cycle`, `block_assignment`, etc. Drops old `block_allocation` |
| `004_labour_sample_data.sql` | Kundasale: 90 employees, 6 groups, 6-round rotation, current week plan |
| `005_remaining_estates_sample_data.sql` | Ramboda / Hunasgiriya / Haputale: blocks, employees, groups, rotation, plans, 4 weeks of history |

### Migration commands

```powershell
python migrate.py migrate          # Run all pending
python migrate.py status           # Show what has / hasn't run
python migrate.py rollback         # DROP everything (dev reset, prompts YES)
```

### Full reset (start fresh)

```powershell
python migrate.py rollback         # type YES
python migrate.py migrate          # re-run all 5 files
```

---

## Common Development Tasks

### Add a new migration

```powershell
# Create the file with the next number
# e.g. 006_add_weather_module.sql

python migrate.py migrate          # picks it up automatically
```

### Inspect the database directly

```powershell
docker exec -it portfolio-db psql -U portfolio -d portfolio
```

Useful psql commands:

```sql
\dt                          -- list all tables
\d block_assignment          -- describe a table
SELECT * FROM estate;        -- view estates
SELECT * FROM v_active_group_members;     -- group headcounts
SELECT * FROM v_current_week_assignments; -- this week's rotation
SELECT * FROM v_rotation_progress;        -- cycle progress per estate
```

### Test a specific API route

```powershell
# Get a token first
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"email":"dev@kvpl.com","password":"Dev@12345"}'
$token = $response.token

# Use it
Invoke-RestMethod -Uri "http://localhost:5000/api/labour/estates" `
  -Headers @{ Authorization = "Bearer $token" }
```

---

## Troubleshooting

### `'charmap' codec can't decode byte` during migration

The migration runner was opening SQL files without specifying encoding.  
**Fix** (already applied): `open(path, 'r', encoding='utf-8')` in `migrate.py`.

---

### `column reference "id" is ambiguous` during migration

A CTE joined two tables that both have an `id` column without qualifying which one.  
**Fix**: Use `b.id`, `wg.id` etc. instead of bare `id` in CTEs that JOIN with `estate`.

---

### `/api/api/labour/...` double-prefix CORS error

The `NEXT_PUBLIC_API_URL` already ends in `/api`, so adding `/api/labour` again makes `/api/api/labour`.  
**Fix** (already applied): The `_labour()` helper in `apiService.js` uses `/labour${path}`, not `/api/labour${path}`.

---

### CORS blocked on preflight

Make sure the Flask backend is running (`python app.py`). Flask-CORS handles all origins in dev mode. If the backend is down, the preflight `OPTIONS` request returns no response, which browsers report as a CORS failure.

---

### `missing FROM-clause entry for table "r3"` in migration

A CTE was named `round3` but referenced as `r3` in the SELECT.  
**Fix** (already applied): Reference matches the CTE name exactly.

---

### Docker port 5432 already in use

A local PostgreSQL service is running alongside Docker.

```powershell
# Windows: stop the local service
Stop-Service postgresql*

# Then restart the container
docker-compose up -d
```

---

### Token expired / 401 after leaving browser idle

Tokens expire after 7 days. Just log out and log back in.  
The frontend auto-refreshes tokens that are within 1 hour of expiry.

---

## Running Everything Together (cheat sheet)

```powershell
# Terminal 1 — Database (run once, stays up)
docker-compose up -d

# Terminal 2 — Backend
cd backend
.venv\Scripts\Activate.ps1
python app.py

# Terminal 3 — Frontend
cd frontend
npm run dev

# Browser
http://localhost:3000
```
