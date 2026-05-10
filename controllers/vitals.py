# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _vitals_dict(vs):
    return {
        'id':               vs.id,
        'visit_id':         vs.visit_id.id if vs.visit_id else None,
        'blood_pressure':   vs.blood_pressure or '',
        'temperature':      vs.temperature,
        'pulse':            vs.pulse,
        'respiratory_rate': vs.respiratory_rate,
        'respiratory_type': vs.respiratory_type or '',
        'o2_saturation':    vs.o2_saturation,
        'weight':           vs.weight,
        'height':           vs.height,
        'bmi':              vs.bmi,
        'recorded_by':      vs.recorded_by.id if vs.recorded_by else None,
        'recorded_by_name': vs.recorded_by.name if vs.recorded_by else '',
        'recorded_at':      str(vs.recorded_at) if vs.recorded_at else None,
    }


class VitalsController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/vitals', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, visit_id, **kw):
        records = request.env['saycare.vital.signs'].sudo().search(
            [('visit_id', '=', visit_id)], order='recorded_at desc'
        )
        return _json([_vitals_dict(vs) for vs in records])

    @http.route('/saycare/api/visit/<int:visit_id>/vitals', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        def _f(val, default=0.0):
            try: return float(val) if val not in (None, '') else default
            except (ValueError, TypeError): return default

        vals = {
            'visit_id':         visit_id,
            'blood_pressure':   body.get('blood_pressure', ''),
            'temperature':      _f(body.get('temperature')),
            'pulse':            _f(body.get('pulse')),
            'respiratory_rate': _f(body.get('respiratory_rate')),
            'respiratory_type': body.get('respiratory_type', 'normal'),
            'o2_saturation':    _f(body.get('o2_saturation')),
            'weight':           _f(body.get('weight')),
            'height':           _f(body.get('height')),
            'recorded_by':      body.get('recorded_by'),
        }
        rec = request.env['saycare.vital.signs'].sudo().create(vals)
        return _json(_vitals_dict(rec), 201)
