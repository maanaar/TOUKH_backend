# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _lab_dict(lo):
    return {
        'id':                lo.id,
        'visit_id':          lo.visit_id.id if lo.visit_id else None,
        'patient_id':        lo.patient_id.id if lo.patient_id else None,
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

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, visit_id, **kw):
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
        vals = {
            'visit_id':     visit_id,
            'patient_id':   body.get('patient_id'),
            'test_name':    body['test_name'],
            'test_code':    body.get('test_code', ''),
            'priority':     body.get('priority', 'routine'),
            'notes':        body.get('notes', ''),
            'requested_by': body.get('requested_by'),
        }
        rec = request.env['saycare.lab.order'].sudo().create(vals)
        return _json(_lab_dict(rec), 201)
