# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
from .utils import _json

AR_DAYS = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']


class DashboardController(http.Controller):

    @http.route('/saycare/api/dashboard/stats', type='http', auth='user', methods=['GET'], csrf=False)
    def stats(self, **kw):
        env = request.env
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start + timedelta(days=1)

        Visit = env['saycare.visit'].sudo()
        Med   = env['saycare.medication.order'].sudo()

        # ── today's visits ──────────────────────────────────────────────────────
        today_visits = Visit.search([
            ('admission_date', '>=', str(today_start)),
            ('admission_date', '<',  str(today_end)),
        ])

        by_state = {}
        for v in today_visits:
            by_state[v.state] = by_state.get(v.state, 0) + 1

        # ── queue sizes ─────────────────────────────────────────────────────────
        nurse_queue  = Visit.search_count([('state', 'in', ['waiting', 'triage'])])
        doctor_queue = Visit.search_count([('state', 'in', ['doctor_queue', 'in_progress'])])

        # ── pharmacy ────────────────────────────────────────────────────────────
        pharmacy_pending = Med.search_count([('state', '=', 'active')])
        pharmacy_dispensed_today = Med.search_count([
            ('state', '=', 'dispensed'),
            ('dispensed_at', '>=', str(today_start)),
            ('dispensed_at', '<',  str(today_end)),
        ])

        # ── total patients ───────────────────────────────────────────────────────
        total_patients = env['res.partner'].sudo().search_count([('is_patient', '=', True)])

        # ── specialties today ────────────────────────────────────────────────────
        spec_counts = {}
        for v in today_visits:
            name = v.specialty_id.name if v.specialty_id else 'غير محدد'
            spec_counts[name] = spec_counts.get(name, 0) + 1
        specialties_today = sorted(
            [{'name': k, 'count': c} for k, c in spec_counts.items()],
            key=lambda x: -x['count']
        )[:6]

        # ── hourly flow today ────────────────────────────────────────────────────
        hourly = {}
        for v in today_visits:
            if v.admission_date:
                h = v.admission_date.hour
                hourly[h] = hourly.get(h, 0) + 1
        hourly_today = [{'hour': h, 'label': f'{h}:00', 'count': hourly.get(h, 0)} for h in range(7, 22)]

        # ── weekly visits (last 7 days) ──────────────────────────────────────────
        weekly_visits = []
        for i in range(6, -1, -1):
            day_start = today_start - timedelta(days=i)
            day_end   = day_start + timedelta(days=1)
            count = Visit.search_count([
                ('admission_date', '>=', str(day_start)),
                ('admission_date', '<',  str(day_end)),
            ])
            weekly_visits.append({
                'day':   AR_DAYS[day_start.weekday()],
                'date':  str(day_start.date()),
                'count': count,
            })

        # ── triage breakdown today ────────────────────────────────────────────────
        triage = [
            {'label': 'في الانتظار', 'count': by_state.get('waiting', 0) + by_state.get('triage', 0), 'color': '#f59e0b'},
            {'label': 'قيد الفحص',   'count': by_state.get('doctor_queue', 0) + by_state.get('in_progress', 0), 'color': '#0ea5e9'},
            {'label': 'مكتمل',       'count': by_state.get('done', 0), 'color': '#10b981'},
        ]

        return _json({
            'visits_today':            len(today_visits),
            'nurse_queue':             nurse_queue,
            'doctor_queue':            doctor_queue,
            'pharmacy_pending':        pharmacy_pending,
            'pharmacy_dispensed_today': pharmacy_dispensed_today,
            'total_patients':          total_patients,
            'by_state':                by_state,
            'triage_breakdown':        triage,
            'specialties_today':       specialties_today,
            'hourly_today':            hourly_today,
            'weekly_visits':           weekly_visits,
        })

    @http.route('/saycare/api/dashboard/visits-today', type='http', auth='user', methods=['GET'], csrf=False)
    def visits_today(self, **kw):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start + timedelta(days=1)

        STATE_LABEL = {
            'waiting':      'في الانتظار',
            'triage':       'قيد الفرز',
            'doctor_queue': 'انتظار الطبيب',
            'in_progress':  'قيد الفحص',
            'done':         'مكتمل',
            'cancelled':    'ملغي',
        }

        visits = request.env['saycare.visit'].sudo().search([
            ('admission_date', '>=', str(today_start)),
            ('admission_date', '<',  str(today_end)),
        ], order='admission_date asc')

        rows = []
        for v in visits:
            p = v.patient_id
            rows.append({
                'id':           v.id,
                'patient_id':   p.id,
                'patient_name': p.name or '—',
                'mrn':          p.mrn or '—',
                'gender':       p.gender or '',
                'dob':          str(p.dob) if p.dob else '',
                'specialty':    v.specialty_id.name if v.specialty_id else '—',
                'doctor':       v.doctor_id.name if v.doctor_id else '—',
                'admission_date': str(v.admission_date) if v.admission_date else '',
                'state':        v.state,
                'state_label':  STATE_LABEL.get(v.state, v.state),
                'visit_type':   v.visit_type or '',
                'financial_class': v.financial_class or '',
            })
        return _json({'visits': rows, 'total': len(rows)})
