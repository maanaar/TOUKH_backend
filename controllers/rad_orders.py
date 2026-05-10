# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _rad_dict(ro):
    return {
        'id':                  ro.id,
        'visit_id':            ro.visit_id.id if ro.visit_id else None,
        'patient_id':          ro.patient_id.id if ro.patient_id else None,
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

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, visit_id, **kw):
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
        vals = {
            'visit_id':            visit_id,
            'patient_id':          body.get('patient_id'),
            'study_type':          body['study_type'],
            'body_part':           body.get('body_part', ''),
            'clinical_indication': body.get('clinical_indication', ''),
            'notes':               body.get('notes', ''),
            'requested_by':        body.get('requested_by'),
        }
        rec = request.env['saycare.rad.order'].sudo().create(vals)
        return _json(_rad_dict(rec), 201)
