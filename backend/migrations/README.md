# Database Migration Setup Instructions

## Overview

This directory contains the KVPL database schema and migration tools. The system uses PostgreSQL with UUID support and includes:

- **4 Core Modules**: Fertilizer Rotation, ROI Calculator, Water Usage Efficiency, Labour Allocation
- **Audit Logging**: Cross-module audit trail
- **Helper Views**: Pre-built queries for common reporting needs
- **Sample Data**: Realistic test data for development

## Files

- `001_initial_schema.sql` - Complete database schema with all tables, indexes, and views
- `002_sample_data.sql` - Sample data for testing and development
- `../migrate.py` - Python migration runner script

## Prerequisites

1. PostgreSQL 12+ installed and running
2. Python 3.8+
3. `psycopg[binary]` installed

## Setup

### 1. Configure Database Connection

Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/kvpl
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=kvpl
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
# Check migration status
python migrate.py status

# Run all pending migrations
python migrate.py migrate

# Run specific migration
python migrate.py migrate --target 001_initial_schema.sql
```

## Migration Management Commands

### Check Status
```bash
python migrate.py status
```
Shows which migrations have been executed and which are pending.

### Run Migrations
```bash
python migrate.py migrate
```
Executes all pending migrations in order. Creates `schema_migrations` table to track progress.

### Development: Full Rollback
```bash
python migrate.py rollback
```
⚠️ **WARNING**: Drops ALL tables and resets migrations. Development only!

## Database Schema Overview

### Core Entities
- `estate` - Agricultural estates/plantations
- `factory` - Processing facilities
- `user` - System users with role-based access
- `block` - Individual tea blocks within estates

### Module 1: Fertilizer Rotation Planner
- `fertilizer_type` - Available fertilizer products
- `fertilizer_application` - Application history
- `fertilizer_recommendation` - AI/system recommendations with override tracking

### Module 2: Input Cost vs Yield ROI Calculator
- `input_cost` - Monthly cost breakdown by category
- `yield_record` - Monthly yield records
- `roi_snapshot` - Computed ROI metrics and rankings

### Module 3: Water Usage Efficiency
- `water_baseline` - Factory baseline water intensity targets
- `water_usage` - Monthly water consumption and tracking status

### Module 4: Labour Allocation Optimizer
- `labour_plan` - Weekly labour allocation plans
- `block_allocation` - Worker allocation to individual blocks

### Cross-Module
- `audit_log` - Complete audit trail of all data changes

## Helper Views

### v_roi_current_month
Current month ROI ranking across all estates.

```sql
SELECT * FROM v_roi_current_month;
```

### v_water_status_latest
Latest water efficiency status per factory.

```sql
SELECT * FROM v_water_status_latest;
```

### v_block_fert_summary
Fertilizer application summary by block (last 12 months).

```sql
SELECT * FROM v_block_fert_summary;
```

## Connecting via Docker Compose

If using the docker-compose setup:

```bash
# Start database
docker-compose up db -d

# Update .env with Docker database URL
# DATABASE_URL=postgresql://your_user:your_password@db:5432/kvpl

# Run migrations
python migrate.py migrate
```

## Sample Data

The `002_sample_data.sql` migration includes:
- 4 estates with realistic names and regions
- 11 blocks across estates
- 8 users with different roles
- 5 months of fertilizer applications
- 5 months of input costs and yield records
- ROI snapshots showing estate rankings
- Water usage data with efficiency tracking
- Labour plans with worker allocations
- Audit log entries

This data is suitable for development and testing workflows.

## Common Tasks

### Add a New Migration

1. Create new SQL file: `003_add_feature.sql`
2. Add schema changes
3. Run: `python migrate.py migrate`

### Connect with Python

```python
import psycopg
from os import getenv

conn = psycopg.connect(getenv('DATABASE_URL'))
cur = conn.cursor()

# Example: Get all estates
cur.execute("SELECT name, region, total_blocks FROM estate")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
```

### Generate Reports

```python
# ROI report for current month
cur.execute("SELECT * FROM v_roi_current_month")

# Water efficiency by factory
cur.execute("SELECT * FROM v_water_status_latest")

# Block fertilizer summary
cur.execute("SELECT * FROM v_block_fert_summary")
```

## Troubleshooting

### Connection Error
```
Failed to connect to database
```
- Verify DATABASE_URL in .env
- Ensure PostgreSQL is running
- Check network connectivity

### Permission Denied
```
permission denied for schema public
```
- Grant privileges: `GRANT ALL ON SCHEMA public TO your_user;`
- Run: `GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;`

### UUID Extension Error
```
extension "uuid-ossp" does not exist
```
- Extension is created automatically in 001_initial_schema.sql
- If missing, manually run: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

### Rollback Failed
Clear schema manually:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO your_user;
```

## Database Indices

For performance, the schema includes indices on:
- Foreign key relationships
- Date-based queries (application_date, recommended_for, week_start)
- Status columns (track_status, is_flagged)
- Time-series lookups (year/month combinations)

## Next Steps

1. Configure `.env` with your database credentials
2. Run `python migrate.py migrate` to set up the database
3. Verify with `python migrate.py status`
4. Build API endpoints using the schema
5. Integrate with Flask application in `app.py`

## Support

For issues or questions about the schema design:
1. Review the SQL comments in migration files
2. Check the helper views for query examples
3. Inspect audit_log for data change history
