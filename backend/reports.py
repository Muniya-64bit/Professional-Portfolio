"""Professional PDF report generator for KVPL estate performance reports.

Dependencies: reportlab, matplotlib  (see requirements.txt)
"""
import io
import logging
from datetime import date, datetime
from decimal import Decimal

import matplotlib
matplotlib.use('Agg')                       # non-interactive, safe for threads
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from flask import Blueprint, jsonify, request, send_file
from auth import token_required, get_db_connection, effective_estate_id

logger = logging.getLogger(__name__)
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

MONTH_NAMES = ['January','February','March','April','May','June',
               'July','August','September','October','November','December']
MONTH_ABBR  = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _f(v):
    return float(v) if isinstance(v, Decimal) else v


def _db():
    return get_db_connection()


# ─────────────────────────────────────────────────────────────────────────────
# Data layer  —  single query pass, returns everything the PDF needs
# ─────────────────────────────────────────────────────────────────────────────

def _fetch(estate_id, year, month):
    conn = _db()
    if not conn:
        return None, 'Database unavailable'

    period_start = date(year, month, 1)
    d = {}

    try:
        with conn.cursor() as cur:
            # Estate
            cur.execute(
                "SELECT id, name, region, total_blocks FROM estate WHERE id = %s",
                (estate_id,))
            row = cur.fetchone()
            if not row:
                return None, 'Estate not found'
            d['estate'] = {
                'id': str(row[0]), 'name': row[1],
                'region': row[2] or '', 'total_blocks': row[3] or 0,
            }

            # Labour plan for this period
            cur.execute(
                "SELECT id, total_workers, target_kg, status "
                "FROM labour_plan "
                "WHERE estate_id = %s AND period_start = %s",
                (estate_id, period_start))
            pr = cur.fetchone()
            d['plan'] = None
            d['assignments'] = []
            if pr:
                d['plan'] = {
                    'id': str(pr[0]), 'total_workers': pr[1] or 0,
                    'target_kg': _f(pr[2]) if pr[2] else 0,
                    'status': pr[3] or 'draft',
                }
                cur.execute("""
                    SELECT b.block_code,
                           wg.group_name, wg.capacity,
                           ba.expected_yield_kg, ba.actual_yield_kg, ba.status
                    FROM block_assignment ba
                    JOIN block b ON b.id = ba.block_id
                    LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                    WHERE ba.labour_plan_id = %s
                    ORDER BY b.block_code
                """, (str(pr[0]),))
                for r in cur.fetchall():
                    exp = _f(r[3]) if r[3] else None
                    act = _f(r[4]) if r[4] else None
                    eff = round(act / exp * 100, 1) if exp and act else None
                    d['assignments'].append({
                        'block': r[0],
                        'group': r[1] or '—',
                        'capacity': r[2] or 0,
                        'expected': exp,
                        'actual':   act,
                        'efficiency': eff,
                        'status': r[5] or 'scheduled',
                    })

            # Worker groups
            cur.execute("""
                SELECT wg.group_code, wg.group_name, wg.capacity,
                       COUNT(wgm.id), sup.full_name
                FROM worker_group wg
                LEFT JOIN worker_group_member wgm
                       ON wgm.group_id = wg.id AND wgm.is_active = TRUE
                LEFT JOIN employee sup ON sup.id = wg.supervisor_id
                WHERE wg.estate_id = %s AND wg.is_active = TRUE
                GROUP BY wg.id, wg.group_code, wg.group_name,
                         wg.capacity, sup.full_name
                ORDER BY wg.group_code
            """, (estate_id,))
            d['groups'] = [
                {'code': r[0], 'name': r[1], 'capacity': r[2] or 0,
                 'headcount': r[3] or 0, 'supervisor': r[4] or '—'}
                for r in cur.fetchall()
            ]

            # Employee breakdown
            cur.execute("""
                SELECT skill_type, employment_type, COUNT(*)
                FROM employee
                WHERE estate_id = %s AND is_active = TRUE
                GROUP BY skill_type, employment_type
            """, (estate_id,))
            emp_rows = cur.fetchall()
            d['total_employees'] = sum(r[2] for r in emp_rows)
            d['by_skill'] = {}
            d['by_type']  = {}
            for skill, etype, cnt in emp_rows:
                d['by_skill'][skill] = d['by_skill'].get(skill, 0) + cnt
                d['by_type'][etype]  = d['by_type'].get(etype, 0)  + cnt

            # Monthly yield totals for the year (for trend chart)
            cur.execute("""
                SELECT byr.month, SUM(byr.yield_kg)
                FROM block_yield_record byr
                JOIN block b ON b.id = byr.block_id
                WHERE b.estate_id = %s AND byr.year = %s
                GROUP BY byr.month ORDER BY byr.month
            """, (estate_id, year))
            d['monthly_yield'] = [
                {'month': r[0], 'yield_kg': _f(r[1])}
                for r in cur.fetchall()
            ]

            # Weather (full year)
            cur.execute("""
                SELECT month, rainfall_mm, avg_temp_c, avg_humidity_pct
                FROM estate_weather
                WHERE estate_id = %s AND year = %s ORDER BY month
            """, (estate_id, year))
            d['weather'] = [
                {'month': r[0], 'rainfall': _f(r[1]) if r[1] else None,
                 'temp':   _f(r[2]) if r[2] else None,
                 'humidity': _f(r[3]) if r[3] else None}
                for r in cur.fetchall()
            ]

        d['year']  = year
        d['month'] = month
        return d, None

    except Exception as e:
        logger.error("Report fetch error: %s", e, exc_info=True)
        return None, str(e)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chart generators  —  each returns a BytesIO PNG or None
# ─────────────────────────────────────────────────────────────────────────────

def _apply_clean_style(ax, show_top=False, show_right=False):
    ax.spines['top'].set_visible(show_top)
    ax.spines['right'].set_visible(show_right)
    ax.tick_params(labelsize=8)


def _save_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def _chart_yield_efficiency(assignments):
    """Grouped horizontal bars: actual vs expected per block."""
    items = [a for a in assignments if a['actual'] is not None]
    if not items:
        return None

    labels   = [a['block'] for a in items]
    expected = [a['expected'] or 0 for a in items]
    actual   = [a['actual']   or 0 for a in items]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(7.5, max(3.0, n * 0.6)))
    y = list(range(n))

    ax.barh([i + 0.22 for i in y], expected, 0.38,
            color='#bfdbfe', label='Expected', zorder=2)

    bar_colors = [
        '#16a34a' if (a / e * 100 >= 100) else
        '#d97706' if (a / e * 100 >= 90)  else '#dc2626'
        for a, e in zip(actual, expected) if e
    ]
    ax.barh([i - 0.22 for i in y], actual, 0.38,
            color=bar_colors, label='Actual', zorder=3)

    # Efficiency % labels
    for i, (a, e) in enumerate(zip(actual, expected)):
        if e and a:
            eff = a / e * 100
            ax.text(max(a, e) + max(actual) * 0.01,
                    i, f'{eff:.0f}%',
                    va='center', fontsize=7.5, fontweight='bold',
                    color='#374151')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9, fontweight='bold')
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}t'))
    ax.set_xlabel('Yield', fontsize=9)
    ax.set_title('Actual vs Expected Yield by Block', fontsize=11,
                 fontweight='bold', pad=14, color='#1e3a5f')
    ax.legend(fontsize=8, loc='lower right',
              framealpha=0.9, edgecolor='#e5e7eb')
    ax.grid(axis='x', alpha=0.2, zorder=1, color='#9ca3af')
    _apply_clean_style(ax)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_monthly_yield(monthly_yield):
    """Bar chart of monthly totals with a trend line overlay."""
    if len(monthly_yield) < 2:
        return None

    months = [MONTH_ABBR[m['month'] - 1] for m in monthly_yield]
    values = [m['yield_kg'] / 1000 for m in monthly_yield]   # tonnes
    x      = list(range(len(months)))

    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    bars = ax.bar(x, values, color='#2563eb', alpha=0.80, zorder=2,
                  width=0.6)

    # Trend line
    if len(values) >= 3:
        import numpy as np
        z = np.polyfit(x, values, 1)
        p = np.poly1d(z)
        ax.plot(x, p(x), '--', color='#f59e0b', lw=1.8, label='Trend', zorder=3)
        ax.legend(fontsize=8, framealpha=0.9)

    # Value labels
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.015,
                f'{v:.1f}t', ha='center', va='bottom',
                fontsize=7.5, fontweight='600', color='#374151')

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=8)
    ax.set_ylabel('Yield (tonnes)', fontsize=9, color='#374151')
    ax.set_title('Monthly Yield Trend', fontsize=11, fontweight='bold',
                 pad=14, color='#1e3a5f')
    ax.grid(axis='y', alpha=0.2, color='#9ca3af', zorder=1)
    _apply_clean_style(ax)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_weather(weather):
    """Dual-axis: rainfall bars + temperature/humidity lines."""
    if len(weather) < 2:
        return None

    months   = [MONTH_ABBR[w['month'] - 1] for w in weather]
    rainfall = [w['rainfall'] or 0 for w in weather]
    temp     = [w['temp']     or 0 for w in weather]
    humidity = [w['humidity'] or 0 for w in weather]
    x = list(range(len(months)))

    fig, ax1 = plt.subplots(figsize=(7.5, 3.2))
    ax2 = ax1.twinx()

    ax1.bar(x, rainfall, color='#60a5fa', alpha=0.65, label='Rainfall (mm)',
            zorder=2, width=0.6)
    ax2.plot(x, temp,     'o-', color='#f59e0b', lw=2,  ms=5,
             label='Avg Temp °C',  zorder=3)
    ax2.plot(x, humidity, 's--', color='#8b5cf6', lw=1.5, ms=4,
             label='Humidity %',   zorder=3)

    ax1.set_xticks(x)
    ax1.set_xticklabels(months, fontsize=8)
    ax1.set_ylabel('Rainfall (mm)', color='#60a5fa', fontsize=9)
    ax2.set_ylabel('°C / %', color='#6b7280', fontsize=9)
    ax1.set_title('Weather Conditions', fontsize=11, fontweight='bold',
                  pad=14, color='#1e3a5f')
    ax1.grid(axis='y', alpha=0.15, zorder=1, color='#9ca3af')
    ax1.spines['top'].set_visible(False)
    ax1.tick_params(labelsize=8)
    ax2.tick_params(labelsize=8)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               fontsize=8, loc='upper left', framealpha=0.9)
    fig.tight_layout()
    return _save_fig(fig)


def _chart_group_fill(groups):
    """Horizontal bar: headcount vs capacity per group."""
    if not groups:
        return None

    labels    = [g['code'] for g in groups]
    capacity  = [g['capacity']  for g in groups]
    headcount = [g['headcount'] for g in groups]

    fig, ax = plt.subplots(figsize=(5.5, max(2.2, len(groups) * 0.5)))
    y = list(range(len(labels)))

    ax.barh(y, capacity,  0.38, color='#e0e7ff', label='Capacity',  zorder=2)
    ax.barh(y, headcount, 0.38, color='#4f46e5', label='Headcount', zorder=3)

    for i, (h, c) in enumerate(zip(headcount, capacity)):
        pct = round(h / c * 100) if c else 0
        ax.text(max(h, c) + max(capacity) * 0.02, i,
                f'{pct}%', va='center', fontsize=7.5,
                fontweight='bold', color='#374151')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9, fontweight='bold')
    ax.set_xlabel('Workers', fontsize=9)
    ax.set_title('Group Headcount vs Capacity', fontsize=10,
                 fontweight='bold', pad=12, color='#1e3a5f')
    ax.legend(fontsize=8, framealpha=0.9)
    ax.grid(axis='x', alpha=0.2, color='#9ca3af')
    _apply_clean_style(ax)
    fig.tight_layout()
    return _save_fig(fig)


# ─────────────────────────────────────────────────────────────────────────────
# PDF builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_pdf(data):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.utils import ImageReader

    W, H   = A4
    MARGIN = 2.0 * cm
    CW     = W - 2 * MARGIN

    # ── Palette ──────────────────────────────────────────────────────────────
    C_PRIMARY = colors.HexColor('#2563eb')
    C_DARK    = colors.HexColor('#1e293b')
    C_SUCCESS = colors.HexColor('#16a34a')
    C_WARNING = colors.HexColor('#d97706')
    C_DANGER  = colors.HexColor('#dc2626')
    C_MUTED   = colors.HexColor('#6b7280')
    C_LIGHT   = colors.HexColor('#f8fafc')
    C_LIGHT2  = colors.HexColor('#eff6ff')
    C_BORDER  = colors.HexColor('#e2e8f0')
    C_WHITE   = colors.white
    C_NAVY    = colors.HexColor('#1e3a5f')

    # ── Style helpers ────────────────────────────────────────────────────────
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    COVER_TITLE  = ps('CT',  fontName='Helvetica-Bold', fontSize=30, textColor=C_DARK,  alignment=TA_CENTER, spaceAfter=12)
    COVER_SUB    = ps('CS',  fontName='Helvetica',      fontSize=12, textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=8)
    COVER_PERIOD = ps('CP',  fontName='Helvetica-Bold', fontSize=18, textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=12)
    SEC_TITLE    = ps('ST',  fontName='Helvetica-Bold', fontSize=13, textColor=C_NAVY,  spaceAfter=4, spaceBefore=10)
    TH           = ps('TH',  fontName='Helvetica-Bold', fontSize=8,  textColor=C_WHITE, alignment=TA_CENTER)
    TD           = ps('TD',  fontName='Helvetica',      fontSize=8,  textColor=C_DARK)
    TD_C         = ps('TDC', fontName='Helvetica',      fontSize=8,  textColor=C_DARK,  alignment=TA_CENTER)
    KPI_V        = ps('KV',  fontName='Helvetica-Bold', fontSize=18, textColor=C_DARK,  alignment=TA_CENTER)
    KPI_L        = ps('KL',  fontName='Helvetica',      fontSize=7,  textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=2)
    BODY         = ps('BD',  fontName='Helvetica',      fontSize=9,  textColor=C_DARK,  spaceAfter=4)
    FOOTER_P     = ps('FP',  fontName='Helvetica',      fontSize=7,  textColor=C_MUTED, alignment=TA_CENTER)

    def eff_color(p):
        if p is None: return C_MUTED
        return C_SUCCESS if p >= 100 else C_WARNING if p >= 90 else C_DANGER

    estate       = data['estate']
    plan         = data['plan']
    assignments  = data['assignments']
    year         = data['year']
    month        = data['month']
    period_label = f"{MONTH_NAMES[month-1]} {year}"
    generated_at = datetime.now().strftime('%d %B %Y  %H:%M')

    exp_total = sum((a['expected'] or 0) for a in assignments)
    act_total = sum((a['actual']   or 0) for a in assignments if a['actual'])
    eff_pct   = round(act_total / exp_total * 100, 1) if exp_total and act_total else None
    tw        = plan['total_workers'] if plan else 0
    kpw       = round(act_total / tw, 1) if tw and act_total else None
    variance  = round(act_total - exp_total) if act_total else None

    # ── Page header/footer callback ──────────────────────────────────────────
    def on_page(canvas, doc):
        canvas.saveState()

        # ── Page border / frame ───────────────────────────────────────────────
        # Outer hairline + inner accent line for a finished, professional look.
        bx = 1.1 * cm
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(1.2)
        canvas.rect(bx, bx, W - 2 * bx, H - 2 * bx)
        canvas.setStrokeColor(C_PRIMARY)
        canvas.setLineWidth(0.4)
        canvas.rect(bx + 0.12 * cm, bx + 0.12 * cm,
                    W - 2 * bx - 0.24 * cm, H - 2 * bx - 0.24 * cm)

        if doc.page > 1:
            canvas.setFont('Helvetica-Bold', 8)
            canvas.setFillColor(C_PRIMARY)
            canvas.drawString(MARGIN, H - MARGIN + 0.45 * cm, estate['name'])
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(C_MUTED)
            canvas.drawRightString(W - MARGIN, H - MARGIN + 0.45 * cm,
                                   f'{period_label} Performance Report')
            canvas.setStrokeColor(C_BORDER)
            canvas.setLineWidth(0.5)
            canvas.line(MARGIN, H - MARGIN + 0.2 * cm,
                        W - MARGIN, H - MARGIN + 0.2 * cm)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(W / 2, MARGIN - 0.6 * cm,
            f'KVPL Plantation Management System  ·  '
            f'Generated: {generated_at}  ·  Page {doc.page}')
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, MARGIN - 0.35 * cm, W - MARGIN, MARGIN - 0.35 * cm)
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=MARGIN + 0.7 * cm, bottomMargin=MARGIN + 0.7 * cm,
        title=f'KVPL {estate["name"]} — {period_label}',
        author='KVPL Plantation Management System',
    )

    HR = lambda: HRFlowable(width=CW, thickness=0.6, color=C_BORDER,
                             spaceAfter=8, spaceBefore=2)

    def from_buf(chart_buf, max_width, max_height):
        """Place a chart preserving its true aspect ratio so it is never
        stretched/squished (which is what makes labels overlap). The image is
        fitted inside the max_width × max_height box and centred."""
        if chart_buf is None:
            return None
        chart_buf.seek(0)
        iw, ih = ImageReader(chart_buf).getSize()
        chart_buf.seek(0)
        aspect = ih / float(iw)
        w = max_width
        h = w * aspect
        if h > max_height:                 # too tall → constrain by height
            h = max_height
            w = h / aspect
        img = Image(chart_buf, width=w, height=h)
        img.hAlign = 'CENTER'
        return img

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 2.5 * cm))
    story.append(Table(
        [[Paragraph('KVPL PLANTATION MANAGEMENT SYSTEM',
            ps('banner', fontName='Helvetica-Bold', fontSize=10,
               textColor=C_WHITE, alignment=TA_CENTER))]],
        colWidths=[CW],
        style=TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), C_PRIMARY),
            ('TOPPADDING',    (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ])
    ))
    story.append(Spacer(1, 2.0 * cm))
    story.append(Paragraph(estate['name'], COVER_TITLE))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph('Estate Performance Report', COVER_SUB))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(period_label, COVER_PERIOD))
    if estate.get('region'):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(estate['region'], COVER_SUB))
    story.append(Spacer(1, 2.0 * cm))
    story.append(HRFlowable(width=CW, thickness=1, color=C_BORDER))
    story.append(Spacer(1, 1.0 * cm))
    story.append(Table([
        ['Generated on:',    generated_at],
        ['Blocks:',          str(estate.get('total_blocks', '—'))],
        ['Plan Status:',     plan['status'].title() if plan else 'No plan this period'],
        ['Employees:',       str(data['total_employees'])],
        ['Worker Groups:',   str(len(data['groups']))],
    ], colWidths=[4 * cm, CW - 4 * cm],
       style=TableStyle([
           ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
           ('FONTSIZE',      (0,0), (-1,-1), 9),
           ('TEXTCOLOR',     (0,0), (0,-1), C_MUTED),
           ('TEXTCOLOR',     (1,0), (1,-1), C_DARK),
           ('TOPPADDING',    (0,0), (-1,-1), 6),
           ('BOTTOMPADDING', (0,0), (-1,-1), 6),
       ])
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph('Executive Summary', SEC_TITLE))
    story.append(HR())

    # 2×4 KPI grid
    def kpi(value, label, color=None):
        vc = color or C_DARK
        # Keep the value on one line — long status words ("Published") would
        # otherwise wrap. Drop the font size a touch for longer strings.
        fs = 18 if len(str(value)) <= 6 else 13
        return [
            Paragraph(str(value),
                ps(f'kv_{label}', fontName='Helvetica-Bold', fontSize=fs,
                   textColor=vc, alignment=TA_CENTER, leading=fs + 2)),
            Paragraph(label, KPI_L),
        ]

    kpi_row1 = [
        kpi(estate.get('total_blocks', '—'), 'Total Blocks'),
        kpi(data['total_employees'],          'Active Employees'),
        kpi(len(data['groups']),              'Worker Groups'),
        kpi(plan['status'].title() if plan else '—', 'Plan Status',
            color=C_SUCCESS if plan else C_MUTED),
    ]
    kpi_row2 = [
        kpi(f"{exp_total/1000:.1f}t" if exp_total else '—', 'Target Yield'),
        kpi(f"{act_total/1000:.1f}t" if act_total else '—', 'Actual Yield',
            color=C_SUCCESS if act_total else C_MUTED),
        kpi(f"{eff_pct}%" if eff_pct else '—', 'Overall Efficiency',
            color=eff_color(eff_pct)),
        kpi(str(round(kpw)) if kpw else '—', 'kg / Worker'),
    ]

    def kpi_inner(cell):
        # cell == [value_paragraph, label_paragraph]; stack them vertically
        # (one column, two rows) so the number sits above its label.
        return Table([[cell[0]], [cell[1]]], style=TableStyle([
            ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING',   (0,0), (-1,-1), 2),
            ('RIGHTPADDING',  (0,0), (-1,-1), 2),
            ('TOPPADDING',    (0,0), (-1,0),  10),  # value row
            ('BOTTOMPADDING', (0,0), (-1,0),  2),
            ('TOPPADDING',    (0,1), (-1,1),  0),   # label row
            ('BOTTOMPADDING', (0,1), (-1,1),  8),
        ]))

    cell_w = CW / 4
    kpi_table = Table(
        [[kpi_inner(kpi_row1[i]) for i in range(4)],
         [kpi_inner(kpi_row2[i]) for i in range(4)]],
        colWidths=[cell_w] * 4,
        style=TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), C_LIGHT),
            ('BACKGROUND',    (0,1), (-1,1), C_LIGHT2),
            ('GRID',          (0,0), (-1,-1), 0.5, C_BORDER),
            ('TOPPADDING',    (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ])
    )
    story.append(kpi_table)

    if variance is not None:
        sign = '+' if variance >= 0 else ''
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            f"{'▲' if variance >= 0 else '▼'}  {sign}{abs(variance):,} kg variance vs target",
            ps('var', fontName='Helvetica-Bold', fontSize=9,
               textColor=C_SUCCESS if variance >= 0 else C_DANGER,
               alignment=TA_CENTER, spaceAfter=4)
        ))

    # ── Labour Plan table ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f'Labour Plan  —  {period_label}', SEC_TITLE))
    story.append(HR())

    if not assignments:
        story.append(Paragraph(
            'No labour plan or assignments found for this period.', BODY))
    else:
        hdr = [Paragraph(h, TH) for h in
               ['Block','Group','Workers','Expected (kg)','Actual (kg)','Efficiency','Status']]
        rows = [hdr]
        for a in assignments:
            eff = a['efficiency']
            rows.append([
                Paragraph(a['block'], ps('bl', fontName='Helvetica-Bold',
                                         fontSize=8, textColor=C_DARK)),
                Paragraph(a['group'],       TD),
                Paragraph(str(a['capacity']), TD_C),
                Paragraph(f"{a['expected']:,.0f}" if a['expected'] else '—', TD_C),
                Paragraph(f"{a['actual']:,.0f}"   if a['actual']   else '—',
                    ps('ac', fontName='Helvetica-Bold', fontSize=8,
                       textColor=C_SUCCESS if a['actual'] else C_MUTED,
                       alignment=TA_CENTER)),
                Paragraph(f"{eff}%" if eff else '—',
                    ps('ef', fontName='Helvetica-Bold', fontSize=8,
                       textColor=eff_color(eff), alignment=TA_CENTER)),
                Paragraph(a['status'],
                    ps('st', fontName='Helvetica', fontSize=7.5, alignment=TA_CENTER,
                       textColor=(C_SUCCESS if a['status'] == 'completed'
                                  else C_WARNING if a['status'] == 'in_progress'
                                  else C_MUTED))),
            ])

        col_w = [CW * f for f in [0.09, 0.22, 0.10, 0.16, 0.14, 0.14, 0.15]]
        story.append(Table(rows, colWidths=col_w, repeatRows=1,
            style=TableStyle([
                ('BACKGROUND',     (0,0), (-1,0),  C_NAVY),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT]),
                ('GRID',           (0,0), (-1,-1),  0.3, C_BORDER),
                ('TOPPADDING',     (0,0), (-1,-1),  5),
                ('BOTTOMPADDING',  (0,0), (-1,-1),  5),
                ('ALIGN',          (0,0), (-1,-1),  'CENTER'),
                ('ALIGN',          (0,1), (1,-1),   'LEFT'),
                ('VALIGN',         (0,0), (-1,-1),  'MIDDLE'),
            ])
        ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — CHARTS: YIELD EFFICIENCY + MONTHLY TREND
    # ══════════════════════════════════════════════════════════════════════════
    chart_eff = _chart_yield_efficiency(assignments)
    if chart_eff:
        img = from_buf(chart_eff, CW, 14 * cm)
        story.append(KeepTogether([
            Paragraph('Yield Efficiency by Block', SEC_TITLE),
            HR(),
            img,
            Spacer(1, 0.5 * cm),
        ]))

    chart_monthly = _chart_monthly_yield(data['monthly_yield'])
    if chart_monthly:
        story.append(KeepTogether([
            Paragraph(f'Monthly Yield Trend — {year}', SEC_TITLE),
            HR(),
            from_buf(chart_monthly, CW, 8 * cm),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — WORKER GROUPS + EMPLOYEES
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph('Worker Groups', SEC_TITLE))
    story.append(HR())

    grp_hdr = [Paragraph(h, TH) for h in
               ['Code','Group Name','Supervisor','Headcount','Capacity','Fill Rate']]
    grp_rows = [grp_hdr]
    for g in data['groups']:
        fill = round(g['headcount'] / g['capacity'] * 100) if g['capacity'] else 0
        fc   = C_SUCCESS if fill >= 90 else C_WARNING if fill >= 60 else C_DANGER
        grp_rows.append([
            Paragraph(g['code'], ps('gc', fontName='Helvetica-Bold', fontSize=8, textColor=C_PRIMARY)),
            Paragraph(g['name'],       TD),
            Paragraph(g['supervisor'], TD),
            Paragraph(str(g['headcount']), TD_C),
            Paragraph(str(g['capacity']),  TD_C),
            Paragraph(f"{fill}%",
                ps('fc', fontName='Helvetica-Bold', fontSize=8,
                   textColor=fc, alignment=TA_CENTER)),
        ])

    story.append(Table(grp_rows,
        colWidths=[CW * f for f in [0.09, 0.26, 0.28, 0.12, 0.12, 0.13]],
        repeatRows=1,
        style=TableStyle([
            ('BACKGROUND',     (0,0), (-1,0),  C_NAVY),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT]),
            ('GRID',           (0,0), (-1,-1),  0.3, C_BORDER),
            ('TOPPADDING',     (0,0), (-1,-1),  5),
            ('BOTTOMPADDING',  (0,0), (-1,-1),  5),
            ('VALIGN',         (0,0), (-1,-1),  'MIDDLE'),
        ])
    ))

    chart_grp = _chart_group_fill(data['groups'])
    if chart_grp:
        story.append(Spacer(1, 0.4 * cm))
        story.append(from_buf(chart_grp, CW * 0.7, 10 * cm))

    # ── Employee summary ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        f'Employee Summary  ({data["total_employees"]} active)', SEC_TITLE))
    story.append(HR())

    # Merge skill + employment type into one flat 4-column table (avoids
    # nested-table negative-width issues in ReportLab).
    emp_hdr = [
        Paragraph('Skill Type',      TH),
        Paragraph('Count',           TH),
        Paragraph('Employment Type', TH),
        Paragraph('Count',           TH),
    ]
    skill_items = sorted(data['by_skill'].items(), key=lambda x: -x[1])
    type_items  = sorted(data['by_type'].items(),  key=lambda x: -x[1])
    n_rows = max(len(skill_items), len(type_items))
    emp_rows = [emp_hdr]
    for i in range(n_rows):
        sk, sc = skill_items[i] if i < len(skill_items) else ('', '')
        ty, tc = type_items[i]  if i < len(type_items)  else ('', '')
        emp_rows.append([
            Paragraph(sk.title() if sk else '', TD),
            Paragraph(str(sc) if sc != '' else '', TD_C),
            Paragraph(ty.title() if ty else '', TD),
            Paragraph(str(tc) if tc != '' else '', TD_C),
        ])

    story.append(Table(emp_rows,
        colWidths=[CW * 0.38, CW * 0.12, CW * 0.38, CW * 0.12],
        repeatRows=1,
        style=TableStyle([
            ('BACKGROUND',     (0,0), (-1,0),  C_NAVY),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT]),
            ('GRID',           (0,0), (-1,-1),  0.3, C_BORDER),
            ('TOPPADDING',     (0,0), (-1,-1),  4),
            ('BOTTOMPADDING',  (0,0), (-1,-1),  4),
            ('VALIGN',         (0,0), (-1,-1),  'MIDDLE'),
            # subtle divider between the two sub-tables
            ('LINEAFTER',      (1,0), (1,-1),   1, C_BORDER),
        ])
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5 — WEATHER
    # ══════════════════════════════════════════════════════════════════════════
    if data['weather']:
        story.append(Paragraph(f'Weather Conditions — {year}', SEC_TITLE))
        story.append(HR())

        wx_hdr = [Paragraph(h, TH) for h in
                  ['Month','Rainfall (mm)','Avg Temp (°C)','Humidity (%)']]
        wx_rows = [wx_hdr]
        for w in data['weather']:
            wx_rows.append([
                Paragraph(MONTH_ABBR[w['month']-1],
                    ps('wm', fontName='Helvetica-Bold', fontSize=8)),
                Paragraph(f"{w['rainfall']:.1f}" if w['rainfall'] else '—', TD_C),
                Paragraph(f"{w['temp']:.1f}"     if w['temp']     else '—', TD_C),
                Paragraph(f"{w['humidity']:.1f}" if w['humidity'] else '—', TD_C),
            ])

        story.append(Table(wx_rows,
            colWidths=[CW * f for f in [0.18, 0.27, 0.27, 0.28]],
            repeatRows=1,
            style=TableStyle([
                ('BACKGROUND',     (0,0), (-1,0),  C_NAVY),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT]),
                ('GRID',           (0,0), (-1,-1),  0.3, C_BORDER),
                ('TOPPADDING',     (0,0), (-1,-1),  5),
                ('BOTTOMPADDING',  (0,0), (-1,-1),  5),
                ('ALIGN',          (0,0), (-1,-1),  'CENTER'),
                ('ALIGN',          (0,1), (0,-1),   'LEFT'),
            ])
        ))

        chart_wx = _chart_weather(data['weather'])
        if chart_wx:
            story.append(Spacer(1, 0.5 * cm))
            story.append(from_buf(chart_wx, CW, 8 * cm))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────────────

@reports_bp.route('/generate', methods=['POST'])
@token_required
def generate_report():
    """POST /api/reports/generate
    Body: { estate_id, year, month }
    Returns: application/pdf attachment
    """
    body      = request.get_json() or {}
    estate_id = body.get('estate_id')
    year      = body.get('year')
    month     = body.get('month')

    if not all([estate_id, year, month]):
        return jsonify({'error': 'estate_id, year and month are required'}), 400

    # Managers may only generate reports for their own estate.
    estate_id, err = effective_estate_id(estate_id)
    if err:
        return err

    try:
        year, month = int(year), int(month)
        if not (1 <= month <= 12):
            raise ValueError('month out of range')
    except (ValueError, TypeError) as e:
        return jsonify({'error': str(e)}), 400

    report_data, err = _fetch(estate_id, year, month)
    if err:
        status = 503 if 'unavailable' in err.lower() else \
                 404 if 'not found'   in err.lower() else 500
        return jsonify({'error': err}), status

    try:
        pdf_buf = _build_pdf(report_data)
    except Exception as e:
        logger.error("PDF build failed: %s", e, exc_info=True)
        return jsonify({'error': f'PDF generation failed: {e}'}), 500

    safe_name = report_data['estate']['name'].replace(' ', '_')
    filename  = f"KVPL_{safe_name}_{year}_{month:02d}_Report.pdf"
    return send_file(
        pdf_buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )
