"""Background scheduler — labour planner + fertilizer status refresh.

Jobs:
  monthly_labour_plan        — 1st of month @ 02:00, generates next month's labour plans
  fertilizer_status_refresh  — daily @ 06:00, promotes pending→due→overdue based on due_date
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from labour import generate_monthly_plans, _next_month
from fertilizer import refresh_schedule_statuses, _run_generate_schedule

logger = logging.getLogger(__name__)

_scheduler = None


def _run_monthly_job():
    """Generate next month's labour plans and fertilizer schedules for all estates."""
    nxt = _next_month(date.today())
    logger.info("Monthly labour job firing for %s", nxt.isoformat())
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
    """Start the background scheduler once (idempotent)."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True)

    # 02:00 on the 1st of every month
    _scheduler.add_job(
        _run_monthly_job,
        trigger='cron', day=1, hour=2, minute=0,
        id='monthly_labour_plan', replace_existing=True,
    )

    # 06:00 every day
    _scheduler.add_job(
        _run_fertilizer_status_refresh,
        trigger='cron', hour=6, minute=0,
        id='fertilizer_status_refresh', replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: monthly_labour_plan @ day=1 02:00, "
        "fertilizer_status_refresh @ 06:00 daily"
    )
    return _scheduler
