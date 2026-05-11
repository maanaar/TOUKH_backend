# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.fields import Datetime as DT
from .utils import _json, _patient_dict

VALID_TRANSITIONS = {
    'waiting':      ['triage', 'doctor_queue', 'cancelled'],
    'triage':       ['doctor_queue', 'cancelled'],
    'doctor_queue': ['in_progress', 'cancelled'],
    'in_progress':  ['done', 'cancelled'],
    'done':         [],
    'cancelled':    [],
}


def _visit_dict(v, full=False):
    from .vitals import _vitals_dict
    from .clinical_notes import _note_dict
    from .medications import _med_dict
    from .lab_orders import _lab_dict
    from .rad_orders import _rad_dict

    d = {
        'id':              v.id,
        'name':            v.name or '',
        'state':           v.state,
        'visit_type':      v.visit_type or '',
        'financial_class': v.financial_class or '',
        'chief_complaint': v.chief_complaint or '',
        'triage_notes':    v.triage_notes or '',
        'admission_date':  str(v.admission_date) if v.admission_date else None,
        'discharge_date':  str(v.discharge_date) if v.discharge_date else None,
        'patient_id':      v.patient_id.id if v.patient_id else None,
        'patient_name':    v.patient_id.name if v.patient_id else '',
        'patient_mrn':     v.patient_id.mrn if v.patient_id else '',
        'doctor_id':       v.doctor_id.id if v.doctor_id else None,
        'doctor_name':     v.doctor_id.name if v.doctor_id else '',
        'nurse_id':        v.nurse_id.id if v.nurse_id else None,
        'nurse_name':      v.nurse_id.name if v.nurse_id else '',
        'specialty_id':    v.specialty_id.id if v.specialty_id else None,
        'specialty_name':  v.specialty_id.name if v.specialty_id else '',
        'notes':           v.notes or '',
    }
    if full:
        d['patient']           = _patient_dict(v.patient_id) if v.patient_id else {}
        d['vitals']            = [_vitals_dict(vs) for vs in v.vital_sign_ids]
        d['medication_orders'] = [_med_dict(m) for m in v.medication_order_ids]
        d['lab_orders']        = [_lab_dict(lo) for lo in v.lab_order_ids]
        d['rad_orders']        = [_rad_dict(ro) for ro in v.rad_order_ids]
        note = v.clinical_note_ids[:1]
        d['clinical_note']     = _note_dict(note[0]) if note else None
    return d


class VisitListController(http.Controller):

    @http.route('/saycare/api/visits', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, date='', date_from='', date_to='', state='', specialty_id='',
                doctor_id='', patient_id='', visit_type='', **kw):
        domain = []
        if date:
            domain += [('admission_date', '>=', f'{date} 00:00:00'),
                       ('admission_date', '<=', f'{date} 23:59:59')]
        else:
            if date_from:
                domain.append(('admission_date', '>=', f'{date_from} 00:00:00'))
            if date_to:
                domain.append(('admission_date', '<=', f'{date_to} 23:59:59'))
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if doctor_id:
            domain.append(('doctor_id', '=', int(doctor_id)))
        if patient_id:
            domain.append(('patient_id', '=', int(patient_id)))
        if visit_type:
            domain.append(('visit_type', '=', visit_type))
        records = request.env['saycare.visit'].sudo().search(
            domain, order='admission_date desc', limit=200
        )
        return _json([_visit_dict(v) for v in records])


class VisitController(http.Controller):

    @http.route('/saycare/api/visit', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('patient_id'):
            return _json({'error': 'patient_id is required'}, 400)
        vals = {
            'patient_id':      body['patient_id'],
            'visit_type':      body.get('visit_type', 'outpatient'),
            'financial_class': body.get('financial_class', ''),
            'chief_complaint': body.get('chief_complaint', ''),
            'specialty_id':    body.get('specialty_id'),
            'doctor_id':       body.get('doctor_id'),
            'notes':           body.get('notes', ''),
        }
        visit = request.env['saycare.visit'].sudo().create(vals)
        if body.get('appointment_id'):
            appt = request.env['saycare.appointment'].sudo().browse(body['appointment_id'])
            if appt.exists():
                appt.write({'visit_id': visit.id, 'state': 'arrived'})
        return _json(_visit_dict(visit), 201)

    @http.route('/saycare/api/visit/<int:visit_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)
        return _json(_visit_dict(v, full=True))

    @http.route('/saycare/api/visit/<int:visit_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        new_state = body.get('state')
        if new_state not in VALID_TRANSITIONS.get(v.state, []):
            return _json({'error': f'cannot transition from {v.state} to {new_state}'}, 400)
        vals = {'state': new_state}
        if body.get('nurse_id'):
            vals['nurse_id'] = body['nurse_id']
        if body.get('triage_notes'):
            vals['triage_notes'] = body['triage_notes']
        if body.get('chief_complaint'):
            vals['chief_complaint'] = body['chief_complaint']
        if new_state == 'done':
            vals['discharge_date'] = DT.now()
        v.write(vals)
        return _json({'ok': True, 'state': v.state,
                      'discharge_date': str(v.discharge_date) if v.discharge_date else None})
