# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from .utils import _json


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


# JS camelCase key -> (odoo field, caster)
_REQUEST_FIELD_MAP = {
    'patientId':              ('patient_id', _int_or_false),
    'source':                 ('source', str),
    'patientName':             ('patient_name', str),
    'fileNumber':              ('file_number', str),
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
        'patientId':              r.patient_id.id if r.patient_id else None,
        'source':                 r.source or '',
        'status':                 r.status or '',
        'patientName':            r.patient_name or '',
        'fileNumber':             r.file_number or '',
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
        'floorId':                r.floor_id.id if r.floor_id else None,
        'stayGradeId':            r.stay_grade_id.id if r.stay_grade_id else None,
        'roomId':                 r.room_id.id if r.room_id else None,
        'bedId':                  r.bed_id.id if r.bed_id else None,
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
    }


class AdmissionRequestController(http.Controller):
    _model = 'saycare.admission.request'

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['GET'], csrf=False)
    def list_requests(self, source='', status='', **kw):
        domain = []
        if source:
            domain.append(('source', '=', source))
        if status:
            domain.append(('status', '=', status))
        records = request.env[self._model].sudo().search(domain, order='create_date desc')
        return _json([_admission_request_dict(r) for r in records])

    @http.route('/saycare/api/admission-requests', type='http', auth='user', methods=['POST'], csrf=False)
    def create_request(self, **kw):
        body, err = _load_body()
        if err:
            return err
        if not (body.get('patientName') or '').strip():
            return _json({'error': 'اسم المريض مطلوب'}, 400)

        vals = _map_body_to_vals(body, _REQUEST_FIELD_MAP)
        rec = request.env[self._model].sudo().create(vals)
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
        if vals:
            rec.write(vals)
        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests/<int:rec_id>/admit', type='http', auth='user', methods=['POST'], csrf=False)
    def admit_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        body, err = _load_body()
        if err:
            return err

        vals = _map_body_to_vals(body.get('requestUpdates') or {}, _REQUEST_FIELD_MAP)
        vals.update(_map_body_to_vals(body.get('admissionDetails') or {}, _ADMISSION_DETAILS_FIELD_MAP))
        vals['status'] = 'admitted'
        vals['admitted_at'] = fields.Datetime.now()
        rec.write(vals)
        return _json(_admission_request_dict(rec))

    @http.route('/saycare/api/admission-requests/<int:rec_id>/cancel', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel_request(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'admission request not found'}, 404)
        rec.write({'status': 'cancelled'})
        return _json(_admission_request_dict(rec))
