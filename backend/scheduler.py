"""Background scheduler — labour planner + fertilizer status refresh.

Jobs:
  monthly_labour_plan        — 1st of month @ 02:00, generates next month's labour plans
  fertilizer_status_refresh  — daily @ 06:00, promotes pending→due→overdue based on due_date
"""
import logging
import os
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from labour import generate_monthly_plans, _next_month
from fertilizer import refresh_schedule_statuses, _run_generate_schedule

logger = logging.getLogger(__name__)

_scheduler = None

# Timezone the cron fires in. Pinned so "02:00 on the 1st" is deterministic
# regardless of the host's local timezone (dev box vs. production server).
SCHEDULER_TIMEZONE = os.environ.get('SCHEDULER_TIMEZONE', 'Asia/Colombo')

# How long after the scheduled instant APScheduler will still run a missed job.
# For a once-a-month job we want it to run even if the process was down at
# exactly 02:00 — anytime within 6 hours of the trigger still counts.
MISFIRE_GRACE_SECONDS = 6 * 60 * 60


def _run_monthly_job():
    """Generate next month's labour plans and fertilizer schedules for all estates.

    Guard: skip silently if the target month is more than one month ahead of
    the latest plan already in the database.  This prevents the scheduler from
    running ahead of real operations when the database only holds seed data up
    to a past month (e.g. Jan–May 2026 seeds while the app runs in June).
    """
    import psycopg, os

    nxt = _next_month(date.today())
    logger.info("Monthly labour job firing for %s", nxt.isoformat())

    try:
        conn = psycopg.connect(os.environ.get('DATABASE_URL'))
        cur  = conn.cursor()
        cur.execute(
            "SELECT MAX(period_start) FROM labour_plan"
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        latest = row[0] if row and row[0] else None
        if latest is not None:
            from datetime import date as _date
            # Allow at most one month ahead of the latest seeded plan
            latest_date = latest if isinstance(latest, _date) else latest.date()
            allowed = _next_month(latest_date)
            if _date(nxt.year, nxt.month, 1) > allowed:
                logger.info(
                    "Monthly labour job skipped — target %s is ahead of "
                    "latest plan %s (next allowed: %s)",
                    nxt.isoformat(), latest_date.isoformat(), allowed.isoformat(),
                )
                return
    except Exception:
        logger.exception("Monthly labour job: guard query failed — proceeding anyway")

    try:
        result, status = generate_monthly_plans(nxt.year, nxt.month)
        logger.info("Monthly labour job done (%s): %s plans created",
                    status, result.get('plans_created'))
    except Exception:
        logger.exception("Monthly labour job failed")

    # Fertilizer schedule generation for each active estate
    try:
        import psycopg
        import os
        conn = psycopg.connect(os.environ['DATABASE_URL'])
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM estate WHERE is_active = TRUE")
            estate_ids = [row[0] for row in cur.fetchall()]
        conn.close()
        for eid in estate_ids:
            payload, http_status = _run_generate_schedule(eid, nxt, user_id=None)
            if http_status == 201:
                logger.info("Fertilizer schedule generated for estate %s: %s", eid, payload)
            elif http_status == 409:
                logger.info("Fertilizer schedule already exists for estate %s %s — skipping", eid, nxt)
            else:
                logger.warning("Fertilizer schedule generation failed for estate %s: %s", eid, payload)
    except Exception:
        logger.exception("Monthly fertilizer schedule job failed")


def _run_fertilizer_status_refresh():
    """Promote stale fertilizer schedule statuses: pending→due→overdue."""
    logger.info("Fertilizer status refresh firing")
    try:
        result = refresh_schedule_statuses()
        logger.info("Fertilizer status refresh done: %s", result)
    except Exception:
        logger.exception("Fertilizer status refresh failed")


def start_scheduler():
    """Start the background scheduler once (idempotent within a process)."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True, timezone=SCHEDULER_TIMEZONE)
    # 02:30 on the 1st of every month, in SCHEDULER_TIMEZONE.
    _scheduler.add_job(
        _run_monthly_job,
        trigger='cron', day=1, hour=2, minute=30,
        id='monthly_labour_plan', replace_existing=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
        coalesce=True,            # collapse multiple missed fires into one run
    )

    # 06:00 every day
    _scheduler.add_job(
        _run_fertilizer_status_refresh,
        trigger='cron', hour=6, minute=0,
        id='fertilizer_status_refresh', replace_existing=True,
    )

    _scheduler.start()
    logger.info("Labour scheduler started (monthly_labour_plan @ day=1 02:30 %s)",
                SCHEDULER_TIMEZONE)
    return _scheduler


def _scheduler_enabled():
    """Decide whether THIS process should own the scheduler.

    * Dev (`python app.py` with the Werkzeug reloader): only the reloader's
      worker process has WERKZEUG_RUN_MAIN == 'true' — start there so the job
      isn't registered twice.
    * Production (gunicorn/uwsgi via wsgi.py): set RUN_SCHEDULER=1 on exactly
      ONE process (a single web worker, or a dedicated scheduler process) so
      the monthly job fires once, not once per worker.
    """
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        return True
    return os.environ.get('RUN_SCHEDULER', '').lower() in ('1', 'true', 'yes')


def maybe_start_scheduler():
    """Start the scheduler only if this process is the designated owner.

    Safe to call at import time (so it runs under wsgi/gunicorn, not just under
    `python app.py`). No-op in processes that aren't the chosen owner.
    """
    if _scheduler_enabled():
        return start_scheduler()
    logger.info("Scheduler not started in this process "
                "(set RUN_SCHEDULER=1 to enable it here)")
    return None
