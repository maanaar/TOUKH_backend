# -*- coding: utf-8 -*-
import datetime
import json
import logging

import pytz

from odoo import http, fields
from odoo.http import request
from .utils import _json

_logger = logging.getLogger(__name__)


def _load_body():
    """Return (body_dict, error_response). error_response is None on success."""
    try:
        return json.loads(request.httprequest.data or '{}'), None
    except json.JSONDecodeError:
        return None, _json({'error': 'invalid JSON'}, 400)


def _int_or_false(v):
    try:
        return int(v) if v not in (None, '', False) else False
    except (TypeError, ValueError):
        return False


def _int_or_zero(v):
    try:
        return int(v) if v not in (None, '', False) else 0
    except (TypeError, ValueError):
        return 0


def _to_datetime_str(v):
    if not v:
        return False
    v = str(v).replace('T', ' ')
    if len(v) == 16:  # YYYY-MM-DD HH:MM
        v += ':00'
    return v


def _to_date_str(v):
    return v or False


def _query_bool(value):
    normalized = str(value or '').strip().lower()

    if normalized in {
        '1',
        'true',
        'yes',
        'y',
        'on',
    }:
        return True

    if normalized in {
        '0',
        'false',
        'no',
        'n',
        'off',
    }:
        return False

    return None


def _local_day_bounds_utc(date_value):
    try:
        selected_date = fields.Date.to_date(date_value)
    except (TypeError, ValueError):
        return None

    if not selected_date:
        return None

    timezone_name = (
        request.env.user.tz
        or request.env.context.get('tz')
        or 'UTC'
    )

    try:
        timezone = pytz.timezone(timezone_name)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.UTC

    start_local = timezone.localize(
        datetime.datetime.combine(
            selected_date,
            datetime.time.min,
        )
    )

    end_local = timezone.localize(
        datetime.datetime.combine(
            selected_date + datetime.timedelta(days=1),
            datetime.time.min,
        )
    )

    start_utc = (
        start_local
        .astimezone(pytz.UTC)
        .replace(tzinfo=None)
    )

    end_utc = (
        end_local
        .astimezone(pytz.UTC)
        .replace(tzinfo=None)
    )

    return (
        fields.Datetime.to_string(start_utc),
        fields.Datetime.to_string(end_utc),
    )


# JS camelCase key -> (odoo field, caster)
_REQUEST_FIELD_MAP = {
    'patientId':              ('patient_id', _int_or_false),
    'source':                 ('source', str),
    'patientName':             ('patient_name', str),
    'fileNumber':              ('x_file_number', str),
    'entryPermitNo':           ('entry_permit_no', str),
    'nationalId':              ('national_id', str),
    'opdVisitNumber':          ('opd_visit_number', str),
    'patientMrn':              ('patient_mrn', str),
    'patientMobile':           ('patient_mobile', str),
    'age':                     ('age', str),
    'gender':                  ('gender', str),
    'address':                 ('address', str),
    'paymentType':             ('payment_type', str),
    'contractEntity':          ('contract_entity', str),
    'coPayPercent':            ('co_pay_percent', str),
    'approvalRequired':        ('approval_required', bool),
    'isInpatient':             ('is_inpatient', bool),
    'isOperation':             ('is_operation', bool),
    'transferType':            ('transfer_type', str),
    'operationName':           ('operation_name', str),
    'operationReason':         ('operation_reason', str),
    'departmentId':            ('department_id', _int_or_false),
    'floorId':                 ('floor_id', _int_or_false),
    'stayGradeId':             ('stay_grade_id', _int_or_false),
    'roomId':                  ('room_id', _int_or_false),
    'bedId':                   ('bed_id', _int_or_false),
    'diagnosis':               ('diagnosis', str),
    'reason':                  ('reason', str),
    'bookingDateTime':         ('booking_datetime', _to_datetime_str),
    'surgeonId':               ('surgeon_id', _int_or_false),
    'surgeonName':             ('surgeon_name', str),
    'doctorName':              ('doctor_name', str),
    'doctorDecisionNotes':     ('doctor_decision_notes', str),
    'priority':                ('priority', str),
    'transferDecisionReason':  ('transfer_decision_reason', str),
    'anesthesiaType':          ('anesthesia_type', str),
    'expectedAdmissionDate':   ('expected_admission_date', _to_date_str),
    'expectedDischargeDate':   ('expected_discharge_date', _to_date_str),
    'maxStayDays':             ('max_stay_days', _int_or_zero),
    'visitId':                 ('visit_id', _int_or_false),
    'worklistStage':           ('worklist_stage', str),
    'isTransfer':              ('is_transfer', bool),
}

# admissionDetails.* -> (odoo field, caster) — applied on top of _REQUEST_FIELD_MAP
_ADMISSION_DETAILS_FIELD_MAP = {
    'ward':                   ('ward', str),
    'bed':                    ('bed', str),
    'paymentType':            ('payment_type', str),
    'attendingDoctor':        ('attending_doctor', str),
    'admissionDate':          ('admission_date', _to_date_str),
    'expectedDischargeDate':  ('expected_discharge_date', _to_date_str),
    'maxStayDays':            ('max_stay_days', _int_or_zero),
    'admissionNotes':         ('admission_notes', str),
}


def _map_body_to_vals(body, field_map):
    vals = {}
    for js_key, (odoo_field, caster) in field_map.items():
        if js_key in body:
            vals[odoo_field] = caster(body[js_key])
    return vals


def _dt_iso(v, with_time=True):
    if not v:
        return ''
    return v.strftime('%Y-%m-%dT%H:%M') if with_time else v.isoformat()


def _admission_request_dict(r):
    return {
        'id':                     r.id,
        'mirroredAppointmentId':  r.mirrored_appointment_id.id if r.mirrored_appointment_id else None,
        'patientId':              r.patient_id.id if r.patient_id else None,
        'source':                 r.source or '',
        'status':                 r.status or '',
        'patientName':            r.patient_name or '',
        'fileNumber':             r.x_file_number or '',
        'entryPermitNo':          r.entry_permit_no or '',
        'nationalId':             r.national_id or '',
        'opdVisitNumber':         r.opd_visit_number or '',
        'patientMrn':             r.patient_mrn or '',
        'patientMobile':          r.patient_mobile or '',
        'age':                    r.age or '',
        'gender':                 r.gender or '',
        'address':                r.address or '',
        'paymentType':            r.payment_type or '',
        'contractEntity':         r.contract_entity or '',
        'coPayPercent':           r.co_pay_percent or '',
        'approvalRequired':       r.approval_required,
        'isInpatient':            r.is_inpatient,
        'isOperation':            r.is_operation,
        'transferType':           r.transfer_type or '',
        'operationName':          r.operation_name or '',
        'operationReason':        r.operation_reason or '',
        'departmentId':           r.department_id.id if r.department_id else None,
        'departmentCare':         bool(r.department_id.care) if r.department_id else False,
        'floorId':                r.floor_id.id if r.floor_id else None,
        'stayGradeId':            r.stay_grade_id.id if r.stay_grade_id else None,
        'roomId':                 r.room_id.id if r.room_id else None,
        'bedId':                  r.bed_id.id if r.bed_id else None,
        'departmentName':         r.department_id.display_name if r.department_id else '',
        'floorName':              r.floor_id.display_name if r.floor_id else '',
        'stayGradeName':          r.stay_grade_id.display_name if r.stay_grade_id else '',
        'roomName':               r.room_id.display_name if r.room_id else '',
        'bedName':                r.bed_id.display_name if r.bed_id else '',
        'diagnosis':              r.diagnosis or '',
        'reason':                 r.reason or '',
        'bookingDateTime':        _dt_iso(r.booking_datetime),
        'surgeonId':              r.surgeon_id.id if r.surgeon_id else None,
        'surgeonName':            r.surgeon_name or '',
        'doctorName':             r.doctor_name or '',
        'doctorDecisionNotes':    r.doctor_decision_notes or '',
        'priority':               r.priority or '',
        'transferDecisionReason': r.transfer_decision_reason or '',
        'anesthesiaType':         r.anesthesia_type or '',
        'expectedAdmissionDate':  _dt_iso(r.expected_admission_date, with_time=False),
        'expectedDischargeDate':  _dt_iso(r.expected_discharge_date, with_time=False),
        'maxStayDays':            r.max_stay_days or 0,
        'inpatientBookingNumber': r.inpatient_booking_number or '',
        'operationBookingNumber': r.operation_booking_number or '',
        'createdAt':              _dt_iso(r.create_date),
        'admittedAt':             _dt_iso(r.admitted_at),
        'admissionDetails': {
            'ward':                  r.ward or '',
            'bed':                   r.bed or '',
            'paymentType':           r.payment_type or '',
            'attendingDoctor':       r.attending_doctor or '',
            'admissionDate':         _dt_iso(r.admission_date, with_time=False),
            'expectedDischargeDate': _dt_iso(r.expected_discharge_date, with_time=False),
            'maxStayDays':           r.max_stay_days or 0,
            'admissionNotes':        r.admission_notes or '',
        },
        'rejectionReason':        r.rejection_reason or '',
        'rejectedAt':             _dt_iso(r.rejected_at),
        'visitId':                r.visit_id.id if r.visit_id else None,
        'worklistStage':          r.worklist_stage or 'booked',
        'isTransfer':             r.is_transfer,
        'saleOrderId':            r.sale_order_id.id if r.sale_order_id else None,
        'saleOrderName':          r.sale_order_id.name if r.sale_order_id else '',
        'billTotal':              r.sale_order_id.amount_total if r.sale_order_id else 0.0,
        'dischargeDate':          _dt_iso(r.discharge_date),
    }


_MIRRORED_APPOINTMENT_SOURCES = ('operation_booking', 'emergency')


def _create_operation_booking_appointment(rec):
    """Mirror an operation-booking or ER-internal-transfer admission request onto
    saycare.appointment so it shows up in "قائمة الحجوزات الداخلي"
    (/unit/appointments/internal). Runs in the same request as the admission-request
    creation so the two can't drift apart — best-effort (must never block the
    admission request itself), so failures are only logged, not raised.
    """
    if rec.source not in _MIRRORED_APPOINTMENT_SOURCES or not rec.patient_id or not rec.booking_datetime:
        return

    try:
        # A savepoint keeps a failure here (e.g. a DB constraint) from aborting the
        # whole transaction — the admission request that was just created must
        # still commit even if this best-effort mirror fails.
        with request.env.cr.savepoint():
            booking_dt = rec.booking_datetime
            start_time = booking_dt.hour + booking_dt.minute / 60.0
            appt = request.env['saycare.appointment'].sudo().create({
                'patient_id':    rec.patient_id.id,
                'date':          booking_dt.date(),
                'start_time':    start_time,
                'end_time':      start_time + 0.25,
                'visit_type':    'inpatient',
                'doctor_id':     rec.surgeon_id.id if rec.surgeon_id else False,
                'department_id': rec.department_id.id if rec.department_id else False,
                'notes':         rec.operation_name if rec.is_operation else (rec.reason or ''),
            })
            rec.mirrored_appointment_id = appt.id
    except Exception:
        _logger.exception(
            'failed to mirror operation-booking admission request %s onto saycare.appointment',
            rec.id,
        )


def _sync_operation_booking_appointment(rec):
    """Keep the mirrored saycare.appointment (see _create_operation_booking_appointment)
    in sync when an operation-booking admission request is edited — otherwise
    "قائمة الحجوزات الداخلي" keeps showing the stale date/doctor/department from
    whenever the request was first created. Best-effort, same as create's mirror."""
    if rec.source not in _MIRRORED_APPOINTMENT_SOURCES or not rec.mirrored_appointment_id or not rec.booking_datetime:
        return
    try:
        with request.env.cr.savepoint():
            booking_dt = rec.booking_datetime
            start_time = booking_dt.hour + booking_dt.minute / 60.0
            rec.mirrored_appointment_id.write({
                'patient_id':    rec.patient_id.id if rec.patient_id else rec.mirrored_appointment_id.patient_id.id,
                'date':          booking_dt.date(),
                'start_time':    start_time,
                'end_time':      start_time + 0.25,
                'doctor_id':     rec.surgeon_id.id if rec.surgeon_id else False,
                'department_id': rec.department_id.id if rec.department_id else False,
                'notes':         rec.operation_name if rec.is_operation else (rec.reason or ''),
            })
    except Exception:
        _logger.exception(
            'failed to sync mirrored appointment for admission request %s',
            rec.id,
        )


class AdmissionRequestController(http.Controller):
    _model = 'saycare.admission.request'

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['GET'], csrf=False)
    def list_requests(
        self,
        source='',
        status='',
        admitted_date='',
        is_inpatient='',
        care='',
        **kw,
    ):
        domain = []

        if source:
            domain.append(('source', '=', source))

        if status:
            domain.append(('status', '=', status))

        inpatient_filter = _query_bool(is_inpatient)

        if inpatient_filter is not None:
            domain.append(
                ('is_inpatient', '=', inpatient_filter)
            )

        care_filter = _query_bool(care)

        if care_filter is True:
            domain.append(('department_id.care', '=', True))
        elif care_filter is False:
            # records with no department at all are not "care" either
            domain.append('|')
            domain.append(('department_id', '=', False))
            domain.append(('department_id.care', '=', False))

        if admitted_date:
            bounds = _local_day_bounds_utc(admitted_date)

            if not bounds:
                return _json(
                    {'error': 'تاريخ القبول غير صحيح'},
                    400,
                )

            start_utc, end_utc = bounds

            domain.extend(
                [
                    ('admitted_at', '>=', start_utc),
                    ('admitted_at', '<', end_utc),
                ]
            )

        order = (
            'admitted_at desc, id desc'
            if status == 'admitted'
            else 'create_date desc'
        )

        records = (
            request.env[self._model]
            .sudo()
            .search(domain, order=order)
        )

        return _json(
            [
                _admission_request_dict(record)
                for record in records
            ]
        )

    @http.route('/saycare/api/admission-requests/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)

        if not rec.exists():
            return _json(
                {'error': 'حالة الحجز الداخلي غير موجودة'},
                404,
            )

        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['POST'], csrf=False)
    def create_request(self, **kw):
        body, err = _load_body()
        if err:
            return err
        if not (body.get('patientName') or '').strip():
            return _json({'error': 'اسم المريض مطلوب'}, 400)

        vals = _map_body_to_vals(body, _REQUEST_FIELD_MAP)
        rec = request.env[self._model].sudo().create(vals)
        _create_operation_booking_appointment(rec)
        return _json(_admission_request_dict(rec), 201)

    @http.route('/saycare/api/admission-requests/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = _map_body_to_vals(body, _REQUEST_FIELD_MAP)
        vals.update(_map_body_to_vals(body.get('admissionDetails') or {}, _ADMISSION_DETAILS_FIELD_MAP))
        if vals:
            previous_bed = rec.bed_id
            rec.write(vals)
            _sync_operation_booking_appointment(rec)
            # A bed edited after admission (e.g. transferring an admitted patient to a
            # different room) must move the occupancy flag too, otherwise the old bed
            # stays marked occupied forever and the bed-map/critical-care dashboards
            # (which read off hospital.bed, not this record) go stale.
            if 'bed_id' in vals and rec.bed_id.id != (previous_bed.id if previous_bed else False):
                if previous_bed:
                    previous_bed.write({'bed_status': 'available', 'current_patient_id': False})
                if rec.bed_id:
                    rec.bed_id.write({
                        'bed_status':          'occupied',
                        'current_patient_id':  rec.patient_id.id if rec.patient_id else False,
                        'last_occupancy_date': fields.Datetime.now(),
                    })
        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests/<int:rec_id>/admit', type='http', auth='user', methods=['POST'], csrf=False)
    def admit_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err

        previous_bed = rec.bed_id

        vals = _map_body_to_vals(body.get('requestUpdates') or {}, _REQUEST_FIELD_MAP)
        vals.update(_map_body_to_vals(body.get('admissionDetails') or {}, _ADMISSION_DETAILS_FIELD_MAP))
        vals['status'] = 'admitted'
        vals['admitted_at'] = fields.Datetime.now()
        vals['worklist_stage'] = 'admission_done'
        rec.write(vals)

        # Admitting a patient to a bed must occupy it immediately — the critical-care
        # and bed-map dashboards read occupancy off hospital.bed, not off this record.
        if rec.bed_id:
            if previous_bed and previous_bed.id != rec.bed_id.id:
                previous_bed.write({'bed_status': 'available', 'current_patient_id': False})
            rec.bed_id.write({
                'bed_status':          'occupied',
                'current_patient_id':  rec.patient_id.id if rec.patient_id else False,
                'last_occupancy_date': fields.Datetime.now(),
            })

        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests/<int:rec_id>/discharge', type='http', auth='user', methods=['POST'], csrf=False)
    def discharge(self, rec_id, **kw):
        """Closes the inpatient Open Bill: stops new charges, confirms the
        admission's running sale.order (if it has any lines — action_confirm's
        own procurement skips any line already fully covered by a done stock
        move, see inpatient_billing.add_bill_line), generates and posts the
        final invoice, and frees the bed immediately instead of relying on
        the 24h auto-free timeout."""
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        if rec.status != 'admitted':
            return _json({'error': 'هذا الحجز لم يتم قبوله بعد'}, 400)
        if rec.worklist_stage == 'discharged':
            return _json({'error': 'تم تسجيل خروج هذا المريض بالفعل'}, 400)

        if rec.bed_id:
            rec.bed_id.write({'bed_status': 'available', 'current_patient_id': False})

        invoice = None
        so = rec.sale_order_id
        if so and so.exists() and so.order_line:
            try:
                if so.state == 'draft':
                    # skip_procurement: every consumable/medicine line on this
                    # order was already physically dispensed (and its stock
                    # move done) the moment it was dispatched during the stay
                    # — see inpatient_billing.add_bill_line — so confirming
                    # here must only finalize pricing, never launch a second,
                    # duplicate delivery for stock that already left the shelf.
                    so.with_context(skip_procurement=True).action_confirm()
                invoices = so._create_invoices()
                for inv in invoices:
                    if inv.state == 'draft' and inv.invoice_line_ids:
                        inv.action_post()
                invoice = invoices[:1]
            except Exception as e:
                _logger.error('discharge: billing failed for admission=%s: %s', rec.id, e, exc_info=True)
                return _json({'error': f'تعذر إصدار الفاتورة النهائية: {e}'}, 500)

        rec.write({
            'worklist_stage': 'discharged',
            'discharge_date': fields.Datetime.now(),
        })

        result = _admission_request_dict(rec)
        result['invoiceId'] = invoice.id if invoice else None
        result['invoiceName'] = invoice.name if invoice else ''
        result['invoiceAmount'] = invoice.amount_total if invoice else 0.0
        return _json(result)

    @http.route('/saycare/api/admission-requests/<int:rec_id>/open-bill/charge', type='http', auth='user', methods=['POST'], csrf=False)
    def add_open_bill_charge(self, rec_id, **kw):
        """Bills arbitrary named items (procedures, or any other one-off
        service that has no dedicated order model of its own — unlike lab/rad,
        which bill via inpatient_billing.bill_service_orders when their own
        saycare.lab.order/rad.order gets created) directly onto the admission's
        Open Bill. Used by DoctorInternal.jsx/InpatientNursingSheetsForm.jsx's
        procedure "طلب" action for inpatient visits, instead of routing through
        the outpatient basket/Reception ad-hoc-invoice flow."""
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        if rec.worklist_stage == 'discharged':
            return _json({'error': 'تم إغلاق فاتورة هذا المريض بعد الخروج — لا يمكن إضافة رسوم جديدة'}, 400)

        body, err = _load_body()
        if err:
            return err
        items = body.get('items') or []
        if not items:
            return _json({'error': 'items is required'}, 400)

        from .inpatient_billing import add_bill_line, _get_or_create_service_product

        added = []
        for item in items:
            name = str(item.get('name') or '').strip()
            price = float(item.get('price') or 0)
            if not name:
                continue

            product = None
            service_id = item.get('service_id')
            raw_service_id = str(service_id or '')
            if raw_service_id.startswith('prod-'):
                # Product-category-sourced item (e.g. procedures picked from
                # a product catalog rather than a saycare.service record) —
                # same id shape rad orders already handle.
                try:
                    tmpl = request.env['product.template'].sudo().browse(int(raw_service_id[5:]))
                    if tmpl.exists():
                        product = tmpl.product_variant_ids[:1]
                except (TypeError, ValueError):
                    product = None
            elif service_id:
                try:
                    svc = request.env['saycare.service'].sudo().browse(int(service_id))
                    if svc.exists() and svc.product_id:
                        product = svc.product_id.product_variant_id
                except (TypeError, ValueError):
                    product = None
            if not product:
                product = _get_or_create_service_product(request.env, name)

            line, _move = add_bill_line(rec, product, 1, price, name, deliver_now=False)
            added.append(line.id)

        return _json({
            'ok':            True,
            'line_ids':      added,
            'sale_order_id': rec.sale_order_id.id if rec.sale_order_id else None,
            'bill_total':    rec.sale_order_id.amount_total if rec.sale_order_id else 0.0,
        })

    @http.route('/saycare/api/admission-requests/open-bills', type='http', auth='user', methods=['GET'], csrf=False)
    def list_open_bills(self, **kw):
        """Admitted-but-not-yet-discharged patients with charges already
        accumulated on their Open Bill (saycare.admission.request.sale_order_id,
        still draft — only becomes a real account.move invoice at discharge).
        Surfaced in فواتير المرضى alongside real invoices, distinguished on
        the frontend, so staff can see what's building up before discharge."""
        admissions = request.env[self._model].sudo().search([
            ('worklist_stage', '!=', 'discharged'),
            ('sale_order_id', '!=', False),
        ], order='admitted_at desc, id desc')
        items = []
        for adm in admissions:
            so = adm.sale_order_id
            if not so.order_line:
                continue
            items.append({
                'id':              adm.id,
                'name':            so.name,
                'partner_name':    adm.patient_id.name if adm.patient_id else (adm.patient_name or ''),
                'date':            str(adm.admitted_at) if adm.admitted_at else str(so.create_date),
                'amount_untaxed':  so.amount_untaxed,
                'amount_total':    so.amount_total,
            })
        return _json({'items': items, 'total': len(items)})

    @http.route('/saycare/api/admission-requests/<int:rec_id>/open-bill', type='http', auth='user', methods=['GET'], csrf=False)
    def get_open_bill(self, rec_id, **kw):
        """Detail view for one admission's in-progress Open Bill — same shape
        as _invoice_dict(full=True) in invoices.py where the two overlap, so
        the existing invoice detail UI can render either with minimal branching,
        but sourced from the sale.order (nothing here is a real invoice yet)."""
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        so = rec.sale_order_id
        if not so or not so.exists():
            return _json({'error': 'لا توجد فاتورة إقامة مفتوحة لهذا المريض بعد'}, 404)

        return _json({
            'id':               rec.id,
            'name':             so.name,
            'state':            'open_bill',
            'payment_state':    'not_paid',
            'partner_id':       rec.patient_id.id if rec.patient_id else None,
            'partner_name':     rec.patient_id.name if rec.patient_id else (rec.patient_name or ''),
            'partner_address':  '',
            'journal_name':     '',
            'invoice_date':     str(rec.admitted_at) if rec.admitted_at else None,
            'invoice_date_due': None,
            'invoice_origin':   rec.inpatient_booking_number or '',
            'narration':        '',
            'currency':         so.currency_id.name if so.currency_id else 'EGP',
            'amount_untaxed':   so.amount_untaxed,
            'amount_tax':       so.amount_tax,
            'amount_total':     so.amount_total,
            'amount_residual':  so.amount_total,
            'payments':         [],
            'lines': [{
                'id':           line.id,
                'name':         line.name or '',
                'product_name': line.product_id.display_name if line.product_id else (line.name or ''),
                'account_name': '',
                'quantity':     line.product_uom_qty,
                'uom_name':     line.product_uom_id.name if line.product_uom_id else '',
                'price_unit':   line.price_unit,
                'tax_names':    ', '.join(t.name for t in line.tax_ids) if line.tax_ids else '',
                'price_total':  line.price_total,
            } for line in so.order_line if line.display_type not in ('line_section', 'line_note')],
        })

    @http.route('/saycare/api/admission-requests/<int:rec_id>/ensure-visit', type='http', auth='user', methods=['POST'], csrf=False)
    def ensure_visit(self, rec_id, **kw):
        """Purely-inpatient admissions (source != an OPD visit) often have no
        linked saycare.visit at all - it's only created when the admission
        originated from a booked OPD visit. Doctor/nurse-originated lab/rad
        requests still need a real visit to attach to (ReceptionPage.jsx's
        pending-request confirm flow requires one), so create one on first
        use rather than assuming it already exists."""
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)

        if rec.visit_id and rec.visit_id.exists():
            return _json({'visit_id': rec.visit_id.id})

        if not rec.patient_id:
            return _json({'error': 'admission request has no patient'}, 400)

        # rec.payment_type stores the Arabic label typed/picked at booking time,
        # not saycare.visit.financial_class's internal Selection key - map it,
        # defaulting to cash for anything unrecognised (never leave it unset,
        # since financial_class drives invoice/treasury logic downstream).
        PAYMENT_TYPE_TO_FINANCIAL_CLASS = {
            'نقدي':          'cash',
            'نفقة الدولة':   'state',
            'جهة تعاقد':     'contract',
            'تعاقدات':       'contract',
            'تأمين صحى':     'insurance',
            'تكافل وكرامة':  'takaful',
            'مشورة':         'consultation',
            'وزارة الصحة':   'moh',
            'عاملين':        'staff',
        }
        financial_class = PAYMENT_TYPE_TO_FINANCIAL_CLASS.get((rec.payment_type or '').strip(), 'cash')

        visit = request.env['saycare.visit'].sudo().create({
            'patient_id':      rec.patient_id.id,
            'visit_type':      'inpatient',
            'department':      rec.department_id.display_name if rec.department_id else '',
            'financial_class': financial_class,
            'contract_entity': rec.contract_entity or '',
            'co_pay_percent':  rec.co_pay_percent or '',
            'chief_complaint': rec.diagnosis or rec.reason or '',
        })
        rec.write({'visit_id': visit.id})
        return _json({'visit_id': visit.id}, 201)

    @http.route('/saycare/api/admission-requests/<int:rec_id>/cancel', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        reason = (body.get('reason') or '').strip()
        if not reason:
            return _json({'error': 'سبب الرفض مطلوب'}, 400)
        rec.write({
            'status': 'cancelled',
            'rejection_reason': reason,
            'rejected_at': fields.Datetime.now(),
        })
        return _json(_admission_request_dict(rec))
