"""Resize worker-group rosters proportional to each group's home-block yield.

Every group was seeded with a flat 15 members.  This redistributes the
NON-supervisor members across the groups of each estate in proportion to the
average predicted yield of the group's home block (its round-1 rotation block),
using the largest-remainder method so the integer sizes sum exactly to the
estate's non-supervisor headcount — nobody is added, removed, or moved to
another estate.

Rules:
  * Supervisors stay anchored to their current group (1 per group).
  * Per-estate total headcount is preserved.
  * worker_group.capacity is updated to the new headcount so the two agree.

Deterministic + idempotent: re-running yields the same rosters.

Run:  python redistribute_groups.py
"""
from dotenv import load_dotenv
load_dotenv()

import os
import psycopg


def largest_remainder(weights, total):
    """Split `total` (int) across keys proportional to weights. Returns {key:int}."""
    keys = list(weights)
    wsum = sum(max(w, 0) for w in weights.values())
    if total <= 0:
        return {k: 0 for k in keys}
    if wsum <= 0:                         # no signal → even split
        base, extra = divmod(total, len(keys))
        return {k: base + (1 if i < extra else 0) for i, k in enumerate(keys)}
    raw   = {k: total * max(weights[k], 0) / wsum for k in keys}
    base  = {k: int(raw[k]) for k in keys}
    short = total - sum(base.values())
    for k in sorted(keys, key=lambda k: raw[k] - base[k], reverse=True)[:short]:
        base[k] += 1
    return base


def main():
    conn = psycopg.connect(os.environ['DATABASE_URL'])
    cur  = conn.cursor()

    cur.execute("SELECT id, name FROM estate ORDER BY name")
    for estate_id, estate_name in cur.fetchall():
        # Groups + home-block (round 1) average predicted yield as the weight
        cur.execute(
            """
            SELECT wg.id, wg.group_code,
                   COALESCE(AVG(yp.predicted_yield_kg), 0) AS home_yield
            FROM worker_group wg
            LEFT JOIN rotation_cycle rc
                   ON rc.estate_id = wg.estate_id AND rc.is_active = TRUE
            LEFT JOIN rotation_round_block rrb
                   ON rrb.rotation_cycle_id = rc.id
                  AND rrb.worker_group_id   = wg.id
                  AND rrb.round_number      = 1
            LEFT JOIN yield_prediction yp
                   ON yp.block_id = rrb.block_id AND yp.year = 2026
            WHERE wg.estate_id = %s AND wg.is_active = TRUE
            GROUP BY wg.id, wg.group_code
            ORDER BY wg.group_code
            """,
            (estate_id,),
        )
        groups = cur.fetchall()
        if not groups:
            continue
        weights = {str(g[0]): float(g[2]) for g in groups}
        codes   = {str(g[0]): g[1] for g in groups}

        # Supervisor members stay put (counted per group)
        cur.execute(
            """
            SELECT wgm.group_id, COUNT(*)
            FROM worker_group_member wgm
            JOIN employee e ON e.id = wgm.employee_id
            WHERE wgm.is_active = TRUE AND e.skill_type = 'supervisor'
              AND e.estate_id = %s
            GROUP BY wgm.group_id
            """,
            (estate_id,),
        )
        sup_per_group = {str(r[0]): r[1] for r in cur.fetchall()}

        # All active NON-supervisor members in this estate (deterministic order)
        cur.execute(
            """
            SELECT wgm.id
            FROM worker_group_member wgm
            JOIN employee e ON e.id = wgm.employee_id
            WHERE wgm.is_active = TRUE AND e.skill_type <> 'supervisor'
              AND e.estate_id = %s
            ORDER BY e.employee_code, wgm.id
            """,
            (estate_id,),
        )
        member_ids = [r[0] for r in cur.fetchall()]

        targets = largest_remainder(weights, len(member_ids))

        # Walk groups in stable order, slice the member list to hit each target
        idx = 0
        summary = []
        for gid in sorted(weights, key=lambda k: codes[k]):
            n = targets[gid]
            slice_ids = member_ids[idx:idx + n]
            idx += n
            if slice_ids:
                cur.execute(
                    "UPDATE worker_group_member SET group_id = %s WHERE id = ANY(%s)",
                    (gid, slice_ids),
                )
            headcount = n + sup_per_group.get(gid, 0)
            cur.execute(
                "UPDATE worker_group SET capacity = %s WHERE id = %s",
                (headcount, gid),
            )
            summary.append(f"{codes[gid]}={headcount}")

        conn.commit()
        print(f"{estate_name}: {len(member_ids)} non-sup + "
              f"{sum(sup_per_group.values())} sup -> " + ", ".join(summary))

    conn.close()


if __name__ == "__main__":
    main()
