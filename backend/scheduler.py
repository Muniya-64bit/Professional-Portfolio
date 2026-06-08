"""Background scheduler for the labour planner.

Runs the monthly plan generation for every estate on the 1st of each month.
The same logic is exposed as POST /api/labour/plans/generate-monthly for
on-demand runs and testing.
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from labour import generate_monthly_plans, _next_month

logger = logging.getLogger(__name__)

_scheduler = None


def _run_monthly_job():
    """Generate next month's labour plans for all estates."""
    nxt = _next_month(date.today())
    logger.info("Monthly labour job firing for %s", nxt.isoformat())
    try:
        result, status = generate_monthly_plans(nxt.year, nxt.month)
        logger.info("Monthly labour job done (%s): %s plans created",
                    status, result.get('plans_created'))
    except Exception:
        logger.exception("Monthly labour job failed")


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
    _scheduler.start()
    logger.info("Labour scheduler started (monthly_labour_plan @ day=1 02:00)")
    return _scheduler
