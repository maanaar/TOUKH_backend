# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json

APPT_VALID_TRANSITIONS = {
    'scheduled':  ['confirmed', 'cancelled'],
    'confirmed':  ['arrived',   'cancelled'],
    'arrived':    ['cancelled'],
    'cancelled':  [],
}


def _appt_dict(a):
    return {
        'id':                a.id,
        'name':              a.name or '',
        'patient_id':        a.patient_id.id if a.patient_id else None,
        'patient_name':      a.patient_id.name if a.patient_id else '',
        'patient_mrn':       getattr(a.patient_id, 'mrn', '') if a.patient_id else '',
        'patient_national_id': getattr(a.patient_id, 'id_number', '') or '' if a.patient_id else '',
        'patient_mobile':      getattr(a.patient_id, 'phone', '') or '' if a.patient_id else '',
        'doctor_id':         a.doctor_id.id if a.doctor_id else None,
        'doctor_name':       a.doctor_id.name if a.doctor_id else '',
        'specialty_id':      a.specialty_id.id if a.specialty_id else None,
        'specialty_name':    a.specialty_id.name if a.specialty_id else '',
        'date':              str(a.date) if a.date else None,
        'start_time':        a.start_time,
        'end_time':          a.end_time,
        'visit_type':        a.visit_type or '',
        'state':             a.state,
        'visit_id':          a.visit_id.id if a.visit_id else None,
        'visit_state':       a.visit_id.state if a.visit_id else None,
        'visit_name':        a.visit_id.name if a.visit_id else '',
        'visit_admission_date': str(a.visit_id.admission_date) if a.visit_id and a.visit_id.admission_date else None,
        'financial_class':   getattr(a.visit_id, 'financial_class', '') or '' if a.visit_id else '',
        'payment_method':    getattr(a.visit_id, 'payment_method', 'cash') or 'cash' if a.visit_id else 'cash',
        'department_id':     a.department_id.id if a.department_id else None,
        'department_name':   a.department_id.display_name if a.department_id else '',
        'department_care':   bool(a.department_id.care) if a.department_id else False,
        'notes':             a.notes or '',
    }


def _query_bool(value):
    normalized = str(value or '').strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return None


class AppointmentController(http.Controller):

    @http.route('/saycare/api/appointments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, date='', doctor_id='', specialty_id='', state='', care='', **kw):
        domain = []
        if date:
            domain.append(('date', '=', date))
        if doctor_id:
            domain.append(('doctor_id', '=', int(doctor_id)))
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if state:
            domain.append(('state', '=', state))
        care_filter = _query_bool(care)
        if care_filter is True:
            domain.append(('department_id.care', '=', True))
        elif care_filter is False:
            domain.append('|')
            domain.append(('department_id', '=', False))
            domain.append(('department_id.care', '=', False))
        records = request.env['saycare.appointment'].sudo().search(
            domain, order='date asc, start_time asc'
        )
        return _json([_appt_dict(a) for a in records])

    @http.route('/saycare/api/appointments/<int:appt_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, appt_id, **kw):
        a = request.env['saycare.appointment'].sudo().browse(appt_id)
        if not a.exists():
            return _json({'error': 'appointment not found'}, 404)
        return _json(_appt_dict(a))

    @http.route('/saycare/api/appointments', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('patient_id') or not body.get('date'):
            return _json({'error': 'patient_id and date are required'}, 400)
        vals = {
            'patient_id':   body['patient_id'],
            'doctor_id':    body.get('doctor_id'),
            'specialty_id': body.get('specialty_id'),
            'date':         body['date'],
            'start_time':   body.get('start_time', 0.0),
            'end_time':     body.get('end_time', 0.0),
            'visit_type':   body.get('visit_type', 'outpatient'),
            'notes':        body.get('notes', ''),
        }
        if body.get('department_id'):
            vals['department_id'] = int(body['department_id'])
        rec = request.env['saycare.appointment'].sudo().create(vals)
        return _json(_appt_dict(rec), 201)

    @http.route('/saycare/api/appointments/<int:appt_id>', type='http', auth='user', methods=['PUT', 'PATCH'], csrf=False)
    def update(self, appt_id, **kw):
        a = request.env['saycare.appointment'].sudo().browse(appt_id)
        if not a.exists():
            return _json({'error': 'appointment not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        # PATCH with {state} triggers state transition
        if 'state' in body:
            new_state = body['state']
            if new_state in APPT_VALID_TRANSITIONS.get(a.state, []):
                a.write({'state': new_state})
            return _json({'ok': True, 'state': a.state})

        allowed = ['doctor_id', 'specialty_id', 'date', 'start_time',
                   'end_time', 'visit_type', 'notes']
        vals = {k: body[k] for k in allowed if k in body}
        a.write(vals)
        return _json(_appt_dict(a))

    @http.route('/saycare/api/appointments/<int:appt_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, appt_id, **kw):
        a = request.env['saycare.appointment'].sudo().browse(appt_id)
        if not a.exists():
            return _json({'error': 'appointment not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        new_state = body.get('state')
        if new_state not in APPT_VALID_TRANSITIONS.get(a.state, []):
            return _json({'error': f'cannot transition from {a.state} to {new_state}'}, 400)
        a.write({'state': new_state})
        return _json({'ok': True, 'state': a.state})
