"""One-shot scheduler demo.

Arms an APScheduler one-time trigger for 01:40 today (local = Sri Lanka time)
and, when it fires, runs the SAME monthly assignment logic the production cron
runs (labour.generate_monthly_plans).  Connects directly to the database via
DATABASE_URL, so it does not need the Flask server to be running.

Run:  python test_scheduler_run.py
"""
import logging
import time as _time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()                       # load DATABASE_URL from backend/.env

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from labour import generate_monthly_plans

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s  %(levelname)s  %(message)s')
log = logging.getLogger('scheduler-demo')

# ── Fire time: 01:40 today, local clock (the PC is on Sri Lanka time) ─────────
_now    = datetime.now()
RUN_AT  = _now.replace(hour=2, minute=35, second=0, microsecond=0)
YEAR, MONTH = 2026, 6               # month the cron would generate next

_done = {'fired': False}


def job():
    log.info("================ MONTHLY ASSIGNMENT JOB FIRING ================")
    result, status = generate_monthly_plans(YEAR, MONTH)
    log.info("generate_monthly_plans(%s, %s) -> HTTP %s, plans_created=%s",
             YEAR, MONTH, status, result.get('plans_created'))
    for r in result.get('results', []):
        log.info("  estate %s | created=%s | round=%s | workers=%s | reason=%s",
                 r.get('estate_id'), r.get('created'),
                 r.get('rotation_round'), r.get('total_workers'),
                 r.get('reason', '-'))
    log.info("==============================================================")
    _done['fired'] = True


sched = BackgroundScheduler()       # defaults to the system local timezone
sched.add_job(job,
              DateTrigger(run_date=RUN_AT),
              id='monthly_assignment_demo',
              misfire_grace_time=3600)   # still run if we arm slightly late
sched.start()
log.info("Armed: will fire at %s (local). Now is %s.",
         RUN_AT.strftime('%Y-%m-%d %H:%M:%S'), _now.strftime('%Y-%m-%d %H:%M:%S'))

# Stay alive until the job has run (hard cap ~20 min as a safety net).
_deadline = _time.time() + 20 * 60
while not _done['fired'] and _time.time() < _deadline:
    _time.sleep(2)

sched.shutdown(wait=False)
log.info("Runner exiting (fired=%s).", _done['fired'])
