# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.fields import Datetime as DT
from .utils import _json

LAB_VALID_TRANSITIONS = {
    'requested':  ['collected', 'cancelled'],
    'collected':  ['resulted',  'cancelled'],
    'resulted':   [],
    'cancelled':  [],
}


def _lab_dict(lo):
    return {
        'id':                lo.id,
        'visit_id':          lo.visit_id.id if lo.visit_id else None,
        'patient_id':        lo.patient_id.id if lo.patient_id else None,
        'patient_name':      lo.patient_id.name if lo.patient_id else '',
        'patient_mrn':       lo.patient_id.mrn if lo.patient_id else '',
        'test_name':         lo.test_name or '',
        'test_code':         lo.test_code or '',
        'priority':          lo.priority or 'routine',
        'notes':             lo.notes or '',
        'state':             lo.state,
        'result_value':      lo.result_value or '',
        'result_at':         str(lo.result_at) if lo.result_at else None,
        'requested_by':      lo.requested_by.id if lo.requested_by else None,
        'requested_by_name': lo.requested_by.name if lo.requested_by else '',
        'requested_at':      str(lo.requested_at) if lo.requested_at else None,
    }


class LabOrderController(http.Controller):

    # ── Per-visit ──────────────────────────────────────────────────────────────

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.lab.order'].sudo().search([('visit_id', '=', visit_id)])
        return _json([_lab_dict(lo) for lo in records])

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('test_name'):
            return _json({'error': 'test_name is required'}, 400)

        # auto-fill patient_id from the visit if not provided
        patient_id = body.get('patient_id')
        if not patient_id:
            visit = request.env['saycare.visit'].sudo().browse(visit_id)
            if visit.exists() and visit.patient_id:
                patient_id = visit.patient_id.id

        vals = {
            'visit_id':     visit_id,
            'patient_id':   patient_id,
            'test_name':    body['test_name'],
            'test_code':    body.get('test_code', ''),
            'priority':     body.get('priority', 'routine'),
            'notes':        body.get('notes', ''),
            'requested_by': body.get('requested_by'),
        }
        rec = request.env['saycare.lab.order'].sudo().create(vals)
        return _json(_lab_dict(rec), 201)

    # ── Global queue ───────────────────────────────────────────────────────────

    @http.route('/saycare/api/lab-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, state='', priority='', date='', **kw):
        domain = []
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if priority:
            domain.append(('priority', '=', priority))
        if date:
            domain += [('requested_at', '>=', f'{date} 00:00:00'),
                       ('requested_at', '<=', f'{date} 23:59:59')]
        records = request.env['saycare.lab.order'].sudo().search(
            domain, order='requested_at asc', limit=500
        )
        return _json([_lab_dict(lo) for lo in records])

    # ── State update ───────────────────────────────────────────────────────────

    @http.route('/saycare/api/lab-orders/<int:order_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, order_id, **kw):
        lo = request.env['saycare.lab.order'].sudo().browse(order_id)
        if not lo.exists():
            return _json({'error': 'lab order not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        new_state = body.get('state')
        if new_state not in LAB_VALID_TRANSITIONS.get(lo.state, []):
            return _json({'error': f'cannot transition from {lo.state} to {new_state}'}, 400)
        vals = {'state': new_state}
        if new_state == 'resulted':
            vals['result_value'] = body.get('result_value', lo.result_value or '')
            vals['result_at']    = DT.now()
        lo.write(vals)
        return _json(_lab_dict(lo))
