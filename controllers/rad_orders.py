# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.fields import Datetime as DT
from .utils import _json

RAD_VALID_TRANSITIONS = {
    'requested':  ['scheduled', 'cancelled'],
    'scheduled':  ['done',      'cancelled'],
    'done':       [],
    'cancelled':  [],
}


def _rad_dict(ro):
    return {
        'id':                  ro.id,
        'visit_id':            ro.visit_id.id if ro.visit_id else None,
        'patient_id':          ro.patient_id.id if ro.patient_id else None,
        'patient_name':        ro.patient_id.name if ro.patient_id else '',
        'patient_mrn':         getattr(ro.patient_id, 'mrn', '') if ro.patient_id else '',
        'study_type':          ro.study_type or '',
        'body_part':           ro.body_part or '',
        'clinical_indication': ro.clinical_indication or '',
        'notes':               ro.notes or '',
        'state':               ro.state,
        'result_notes':        ro.result_notes or '',
        'result_at':           str(ro.result_at) if ro.result_at else None,
        'requested_by':        ro.requested_by.id if ro.requested_by else None,
        'requested_by_name':   ro.requested_by.name if ro.requested_by else '',
        'requested_at':        str(ro.requested_at) if ro.requested_at else None,
    }


class RadOrderController(http.Controller):

    # ── Per-visit ──────────────────────────────────────────────────────────────

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.rad.order'].sudo().search([('visit_id', '=', visit_id)])
        return _json([_rad_dict(ro) for ro in records])

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('study_type'):
            return _json({'error': 'study_type is required'}, 400)

        # auto-fill patient_id from the visit if not provided
        patient_id = body.get('patient_id')
        if not patient_id:
            visit = request.env['saycare.visit'].sudo().browse(visit_id)
            if visit.exists() and visit.patient_id:
                patient_id = visit.patient_id.id

        vals = {
            'visit_id':            visit_id,
            'patient_id':          patient_id,
            'study_type':          body['study_type'],
            'body_part':           body.get('body_part', ''),
            'clinical_indication': body.get('clinical_indication', ''),
            'notes':               body.get('notes', ''),
            'requested_by':        body.get('requested_by'),
        }
        rec = request.env['saycare.rad.order'].sudo().create(vals)
        return _json(_rad_dict(rec), 201)

    # ── Global queue ───────────────────────────────────────────────────────────

    @http.route('/saycare/api/rad-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, state='', study_type='', date='', patient_id='', **kw):
        domain = []
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if study_type:
            domain.append(('study_type', '=', study_type))
        if date:
            domain += [('requested_at', '>=', f'{date} 00:00:00'),
                       ('requested_at', '<=', f'{date} 23:59:59')]
        if patient_id:
            try:
                domain.append(('patient_id', '=', int(patient_id)))
            except (ValueError, TypeError):
                pass
        records = request.env['saycare.rad.order'].sudo().search(
            domain, order='requested_at asc', limit=500
        )
        return _json([_rad_dict(ro) for ro in records])

    # ── State update ───────────────────────────────────────────────────────────

    @http.route('/saycare/api/rad-orders/<int:order_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, order_id, **kw):
        ro = request.env['saycare.rad.order'].sudo().browse(order_id)
        if not ro.exists():
            return _json({'error': 'rad order not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        new_state = body.get('state')
        if new_state not in RAD_VALID_TRANSITIONS.get(ro.state, []):
            return _json({'error': f'cannot transition from {ro.state} to {new_state}'}, 400)
        vals = {'state': new_state}
        if new_state == 'done':
            vals['result_notes'] = body.get('result_notes', ro.result_notes or '')
            vals['result_at']    = DT.now()
        ro.write(vals)
        return _json(_rad_dict(ro))
