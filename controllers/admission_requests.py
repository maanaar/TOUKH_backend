# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from .utils import _json

_MODEL = 'saycare.admission.request'

# camelCase (frontend) -> backend field name, for plain scalar fields only.
_FIELD_MAP = {
    'nationalId':       'national_id',
    'fileNumber':       'file_number',
    'patientMrn':       'file_number',
    'entryPermitNo':    'entry_permit_no',
    'patientMobile':    'patient_mobile',
    'age':              'age',
    'gender':           'gender',
    'address':          'address',
    'opdVisitNumber':   'opd_visit_number',
    'paymentType':      'payment_type',
    'contractEntity':   'contract_entity',
    'coPayPercent':     'co_pay_percent',
    'approvalRequired': 'approval_required',
    'isInpatient':      'is_inpatient',
    'isOperation':      'is_operation',
    'transferType':     'transfer_type',
    'operationName':    'operation_name',
    'operationReason':  'operation_reason',
    'anesthesiaType':   'anesthesia_type',
    'diagnosis':        'diagnosis',
    'reason':           'reason',
    'transferDecisionReason': 'transfer_decision_reason',
    'bookingDateTime':       'booking_datetime',
    'expectedAdmissionDate': 'expected_admission_date',
    'expectedDischargeDate': 'expected_discharge_date',
    'maxStayDays':           'max_stay_days',
    'surgeonName':  'surgeon_name',
    'doctorName':   'doctor_name',
    'doctorDecisionNotes': 'doctor_decision_notes',
    'priority':     'priority',
}
_M2O_MAP = {
    'departmentId': 'department_id',
    'floorId':      'floor_id',
    'stayGradeId':  'stay_grade_id',
    'roomId':       'room_id',
    'bedId':        'bed_id',
    'surgeonId':    'surgeon_id',
}


def _load_body():
    try:
        return json.loads(request.httprequest.data or '{}'), None
    except json.JSONDecodeError:
        return None, _json({'error': 'invalid JSON'}, 400)


def _normalize_datetime(value):
    """Frontend <input type="datetime-local"> sends 'YYYY-MM-DDTHH:MM' (no
    seconds, 'T' separator) — Odoo's Datetime field needs 'YYYY-MM-DD HH:MM:SS'."""
    if not value:
        return value
    value = value.replace('T', ' ')
    if len(value) == 16:  # 'YYYY-MM-DD HH:MM'
        value += ':00'
    return value


def _vals_from_body(body):
    vals = {}
    for key, field in _FIELD_MAP.items():
        if key in body:
            vals[field] = body[key]
    for key, field in _M2O_MAP.items():
        if key in body:
            vals[field] = int(body[key]) if body[key] else False
    if 'patientName' in body:
        vals['patient_name'] = body['patientName']
    if 'patientId' in body:
        vals['patient_id'] = int(body['patientId']) if body['patientId'] else False
    if 'booking_datetime' in vals:
        vals['booking_datetime'] = _normalize_datetime(vals['booking_datetime'])
    return vals


class AdmissionRequestController(http.Controller):

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['GET'], csrf=False)
    def list_all(self, source='', status='', **kw):
        domain = []
        if source:
            domain.append(('source', '=', source))
        if status:
            domain.append(('status', '=', status))
        records = request.env[_MODEL].sudo().search(domain)
        return _json([r._to_dict() for r in records])

    @http.route('/saycare/api/admission-requests/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        return _json(rec._to_dict())

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        if not (body.get('patientName') or '').strip():
            return _json({'error': 'patientName is required'}, 400)

        vals = _vals_from_body(body)
        vals['source'] = body.get('source') or 'operation_booking'
        vals['status'] = 'pending_admission'
        rec = request.env[_MODEL].sudo().create(vals)
        return _json(rec._to_dict(), 201)

    @http.route('/saycare/api/admission-requests/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = _vals_from_body(body)
        if vals:
            rec.write(vals)
        return _json(rec._to_dict())

    @http.route('/saycare/api/admission-requests/<int:rec_id>/admit', type='http', auth='user', methods=['POST'], csrf=False)
    def admit(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        if rec.status == 'admitted':
            return _json(rec._to_dict())

        # Any corrected case-data fields (e.g. إذن الدخول, رقم الملف) sent alongside admit.
        request_updates = body.get('requestUpdates') or {}
        vals = _vals_from_body(request_updates)

        admission = body.get('admissionDetails') or {}
        vals.update({
            'admission_ward':             admission.get('ward') or '',
            'admission_bed':              admission.get('bed') or '',
            'admission_payment_type':     admission.get('paymentType') or '',
            'admission_attending_doctor': admission.get('attendingDoctor') or '',
            'admission_date':             admission.get('admissionDate') or fields.Date.today(),
            'admission_expected_discharge_date': admission.get('expectedDischargeDate') or False,
            'admission_max_stay_days':    int(admission.get('maxStayDays') or 0),
            'admission_notes':            admission.get('admissionNotes') or '',
            'status':      'admitted',
            'admitted_at': fields.Datetime.now(),
        })
        rec.write(vals)

        # Reflect the admission on the real appointments calendar/list.
        if rec.patient_id:
            start_dt = rec.booking_datetime or fields.Datetime.now()
            request.env['saycare.appointment'].sudo().create({
                'patient_id':  rec.patient_id.id,
                'doctor_id':   rec.surgeon_id.id if rec.surgeon_id else False,
                'date':        start_dt.date(),
                'start_time':  start_dt.hour + start_dt.minute / 60.0,
                'end_time':    start_dt.hour + start_dt.minute / 60.0 + 1.0,
                'visit_type':  'inpatient',
                'state':       'confirmed',
                'notes':       f'حجز داخلي - {rec.inpatient_booking_number}',
            })

        return _json(rec._to_dict())

    @http.route('/saycare/api/admission-requests/<int:rec_id>/cancel', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        rec.write({'status': 'cancelled'})
        return _json(rec._to_dict())
