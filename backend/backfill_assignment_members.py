"""Backfill block_assignment_member for every existing labour plan.

Existing plans (Jan–Jun 2026) were generated before the per-month membership
snapshot existed.  This walks every plan and runs the same assignment logic
(labour._snapshot_assignment_members) so historical group membership becomes
queryable.  Idempotent — re-running rebuilds each plan's snapshot.

Run:  python backfill_assignment_members.py
"""
from dotenv import load_dotenv
load_dotenv()

import os
import psycopg

from labour import _snapshot_assignment_members


def main():
    conn = psycopg.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    cur.execute(
        """SELECT lp.id, e.name, lp.period_start
           FROM labour_plan lp JOIN estate e ON e.id = lp.estate_id
           ORDER BY e.name, lp.period_start"""
    )
    plans = cur.fetchall()
    total = 0
    for plan_id, estate_name, period in plans:
        n = _snapshot_assignment_members(cur, plan_id)
        conn.commit()
        total += n
        print(f"{estate_name:20} {period}  -> {n} members")
    print(f"\nBackfilled {total} member rows across {len(plans)} plans.")
    conn.close()


if __name__ == "__main__":
    main()
