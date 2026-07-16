# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
from .utils import _json

AR_DAYS = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']


class DashboardController(http.Controller):

    @http.route('/saycare/api/dashboard/stats', type='http', auth='user', methods=['GET'], csrf=False)
    def stats(self, date_from='', date_to='', **kw):
        env = request.env

        # "today" is only used as an anchor for the always-relative KPIs
        # (dispensed-today, weekly trend) — it must not depend on the filter.
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start + timedelta(days=1)

        # ── requested range for the visit list/stats — empty means "all data" ───
        range_start = range_end = None
        try:
            if date_from:
                range_start = datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            if date_to:
                range_end = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            range_start = range_end = None

        Visit = env['saycare.visit'].sudo()
        Med   = env['saycare.medication.order'].sudo()

        # ── visits for the requested range (no bounds → all data) ───────────────
        visit_domain = []
        if range_start:
            visit_domain.append(('admission_date', '>=', str(range_start)))
        if range_end:
            visit_domain.append(('admission_date', '<=', str(range_end)))
        today_visits = Visit.search(visit_domain)

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

    @http.route('/saycare/api/dashboard/clinics-overview', type='http', auth='user', methods=['GET'], csrf=False)
    def clinics_overview(self, date_from='', date_to='', **kw):
        env = request.env

        range_start = range_end = None
        try:
            if date_from:
                range_start = datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            if date_to:
                range_end = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            range_start = range_end = None

        Visit      = env['saycare.visit'].sudo()
        Med        = env['saycare.medication.order'].sudo()
        Admission  = env['saycare.admission.request'].sudo()

        visit_domain = [('state', '!=', 'cancelled')]
        if range_start:
            visit_domain.append(('admission_date', '>=', str(range_start)))
        if range_end:
            visit_domain.append(('admission_date', '<=', str(range_end)))
        visits = Visit.search(visit_domain)

        # ── 1) حجز العيادات: العيادة - الدكتور - الفئة - عدد الحالات ─────────────
        GRADE_LABEL = {'consultant': 'استشاري', 'specialist': 'أخصائي'}
        booking_counts = {}
        for v in visits:
            specialty_name = v.specialty_id.name if v.specialty_id else 'غير محدد'
            doctor_name    = v.doctor_id.name if v.doctor_id else 'غير محدد'
            grade          = v.doctor_id.doctor_grade if v.doctor_id else False
            key = (specialty_name, doctor_name, grade)
            booking_counts[key] = booking_counts.get(key, 0) + 1
        clinic_bookings = sorted([
            {
                'specialty': specialty_name,
                'doctor':    doctor_name,
                'grade':     grade or '',
                'grade_label': GRADE_LABEL.get(grade, 'غير محدد'),
                'count':     count,
            }
            for (specialty_name, doctor_name, grade), count in booking_counts.items()
        ], key=lambda x: -x['count'])

        # ── 2) عدد حالات الصرف من الصيدلية ────────────────────────────────────────
        med_domain = [('state', '=', 'dispensed')]
        if range_start:
            med_domain.append(('dispensed_at', '>=', str(range_start)))
        if range_end:
            med_domain.append(('dispensed_at', '<=', str(range_end)))
        pharmacy_dispensed_count = Med.search_count(med_domain)

        # ── 3) نسبة اكتمال تشخيص/إجراءات الطبيب لكل عيادة (تقديري: وجود ملاحظة سريرية) ─
        # ── 4) نسبة اكتمال إجراءات التمريض لكل عيادة (تقديري: وجود قياسات حيوية) ─────
        doctor_stage_visits = visits.filtered(lambda v: v.state in ('doctor_queue', 'in_progress', 'done'))
        by_specialty = {}
        for v in visits:
            name = v.specialty_id.name if v.specialty_id else 'غير محدد'
            by_specialty.setdefault(name, {'nurse_total': 0, 'nurse_done': 0, 'doctor_total': 0, 'doctor_done': 0})
            by_specialty[name]['nurse_total'] += 1
            if v.vital_sign_ids:
                by_specialty[name]['nurse_done'] += 1
        for v in doctor_stage_visits:
            name = v.specialty_id.name if v.specialty_id else 'غير محدد'
            by_specialty.setdefault(name, {'nurse_total': 0, 'nurse_done': 0, 'doctor_total': 0, 'doctor_done': 0})
            by_specialty[name]['doctor_total'] += 1
            if v.clinical_note_ids:
                by_specialty[name]['doctor_done'] += 1

        def _rate(done, total):
            return round((done / total) * 100, 1) if total else 0.0

        doctor_completion = sorted([
            {
                'specialty': name,
                'total':     data['doctor_total'],
                'completed': data['doctor_done'],
                'rate':      _rate(data['doctor_done'], data['doctor_total']),
            }
            for name, data in by_specialty.items() if data['doctor_total']
        ], key=lambda x: -x['total'])

        nursing_completion = sorted([
            {
                'specialty': name,
                'total':     data['nurse_total'],
                'completed': data['nurse_done'],
                'rate':      _rate(data['nurse_done'], data['nurse_total']),
            }
            for name, data in by_specialty.items() if data['nurse_total']
        ], key=lambda x: -x['total'])

        # ── 5) عدد مرضى قسم الداخلي وفقاً للقسم والفئة المالية ─────────────────────
        # care=true departments are surfaced only in the critical-care dashboard.
        admission_domain = [
            ('status', '=', 'admitted'),
            '|', ('department_id', '=', False), ('department_id.care', '=', False),
        ]
        if range_start:
            admission_domain.append(('create_date', '>=', str(range_start)))
        if range_end:
            admission_domain.append(('create_date', '<=', str(range_end)))
        admissions = Admission.search(admission_domain)
        inpatient_counts = {}
        for a in admissions:
            dept_name = a.department_id.name_ar if a.department_id else 'غير محدد'
            fin_class = a.payment_type or 'غير محدد'
            key = (dept_name, fin_class)
            inpatient_counts[key] = inpatient_counts.get(key, 0) + 1
        inpatient_by_department = sorted([
            {'department': dept_name, 'financial_class': fin_class, 'count': count}
            for (dept_name, fin_class), count in inpatient_counts.items()
        ], key=lambda x: -x['count'])

        return _json({
            'clinic_bookings':          clinic_bookings,
            'pharmacy_dispensed_count': pharmacy_dispensed_count,
            'doctor_completion':        doctor_completion,
            'nursing_completion':       nursing_completion,
            'inpatient_by_department':  inpatient_by_department,
        })

    @http.route('/saycare/api/dashboard/critical-care', type='http', auth='user', methods=['GET'], csrf=False)
    def critical_care(self, department_id='', **kw):
        env = request.env

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start + timedelta(days=1)

        GENERAL_CONDITION_LABEL = {
            'stable':           'مستقر',
            'unstable':         'غير مستقر',
            'critical':         'حرج',
            'immediate_review': 'يحتاج مراجعة فورية',
        }

        Department = env['hospital.inpatient.department'].sudo()
        Room       = env['hospital.room'].sudo()
        Bed        = env['hospital.bed'].sudo()
        Admission  = env['saycare.admission.request'].sudo()
        Assessment = env['saycare.inpatient.nursing.assessment'].sudo()

        dept_domain = [('care', '=', True), ('active', '=', True)]
        if department_id:
            dept_domain.append(('id', '=', int(department_id)))
        departments = Department.search(dept_domain)

        units = []
        total_beds = total_occupied = total_critical = 0
        total_ventilators = total_admissions_today = total_transfers_today = total_pending = 0

        for dept in departments:
            image_url = f'/web/image/hospital.inpatient.department/{dept.id}/image' if dept.image else ''

            rooms = Room.search([('department_id', '=', dept.id), ('active', '=', True)])
            beds  = Bed.search([('room_id', 'in', rooms.ids), ('active', '=', True)]) if rooms else Bed.browse()

            bed_total     = len(beds)
            occupied_beds = beds.filtered(lambda b: b.bed_status == 'occupied')
            bed_occupied  = len(occupied_beds)
            bed_available = len(beds.filtered(lambda b: b.bed_status == 'available'))
            occupancy_pct = round((bed_occupied / bed_total) * 100) if bed_total else 0
            ventilators_in_use = len(occupied_beds.filtered(lambda b: b.has_ventilator))

            # A care=true department is tracked from the moment a request targets it —
            # pending_admission cases show up here immediately, not only once admitted.
            current = Admission.search([
                ('department_id', '=', dept.id),
                ('status', 'in', ['admitted', 'pending_admission']),
            ])
            assessments = Assessment.search([('admission_request_id', 'in', current.ids)])
            condition_by_admission = {a.admission_request_id.id: a.general_condition for a in assessments}

            critical_count = sum(
                1 for a in current if condition_by_admission.get(a.id) == 'critical'
            )
            admitted_today = current.filtered(
                lambda a: a.admitted_at and today_start <= a.admitted_at < today_end
            )
            admissions_today = sum(1 for a in admitted_today if not a.is_transfer)
            transfers_today  = sum(1 for a in admitted_today if a.is_transfer)
            pending_count = sum(1 for a in current if a.status == 'pending_admission')

            patients = [{
                'admissionId':            a.id,
                'patientName':            a.patient_name or a.patient_id.display_name or '—',
                'patientMrn':             a.patient_mrn or '',
                'inpatientBookingNumber': a.inpatient_booking_number or '',
                'roomName':               a.room_id.display_name if a.room_id else '',
                'bedName':                a.bed_id.display_name if a.bed_id else '—',
                'attendingDoctor':        a.attending_doctor or a.doctor_name or '',
                'status':                 a.status or '',
                'worklistStage':          a.worklist_stage or 'booked',
                'generalCondition':       condition_by_admission.get(a.id) or '',
                'generalConditionLabel':  GENERAL_CONDITION_LABEL.get(condition_by_admission.get(a.id), ''),
                'admissionDate':          str(a.admission_date) if a.admission_date else '',
                'bookingDateTime':        a.booking_datetime.strftime('%Y-%m-%dT%H:%M') if a.booking_datetime else '',
            } for a in current]

            units.append({
                'id':                 dept.id,
                'code':               dept.code or '',
                'name':               dept.name_ar or '',
                'departmentId':       dept.id,
                'departmentName':     dept.name_ar or '',
                'departmentImageUrl': image_url,
                'bedTotal':           bed_total,
                'bedOccupied':        bed_occupied,
                'bedAvailable':       bed_available,
                'occupancyPct':       occupancy_pct,
                'ventilatorsInUse':   ventilators_in_use,
                'criticalCount':      critical_count,
                'admissionsToday':    admissions_today,
                'transfersToday':     transfers_today,
                'pendingCount':       pending_count,
                'patients':           patients,
            })

            total_beds              += bed_total
            total_occupied           += bed_occupied
            total_critical           += critical_count
            total_ventilators        += ventilators_in_use
            total_admissions_today   += admissions_today
            total_transfers_today    += transfers_today
            total_pending            += pending_count

        units.sort(key=lambda u: -u['occupancyPct'])

        overall_occupancy_pct = round((total_occupied / total_beds) * 100) if total_beds else 0

        return _json({
            'summary': {
                'totalUnits':        len(units),
                'totalBeds':         total_beds,
                'totalOccupied':     total_occupied,
                'totalAvailable':    total_beds - total_occupied,
                'occupancyPct':      overall_occupancy_pct,
                'ventilatorsInUse':  total_ventilators,
                'criticalCount':     total_critical,
                'admissionsToday':   total_admissions_today,
                'transfersToday':    total_transfers_today,
                'pendingCount':      total_pending,
            },
            'units': units,
        })

    @http.route('/saycare/api/dashboard/visits-today', type='http', auth='user', methods=['GET'], csrf=False)
    def visits_today(self, date_from='', date_to='', **kw):
        # No date_from/date_to at all → no restriction, return all visits.
        domain = []
        try:
            if date_from:
                range_start = datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                domain.append(('admission_date', '>=', str(range_start)))
            if date_to:
                range_end = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                domain.append(('admission_date', '<=', str(range_end)))
        except ValueError:
            domain = []

        STATE_LABEL = {
            'waiting':      'في الانتظار',
            'triage':       'قيد الفرز',
            'doctor_queue': 'انتظار الطبيب',
            'in_progress':  'قيد الفحص',
            'done':         'مكتمل',
            'cancelled':    'ملغي',
        }

        visits = request.env['saycare.visit'].sudo().search(domain, order='admission_date asc')

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
