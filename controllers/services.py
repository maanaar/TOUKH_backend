# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _service_dict(s):
    return {
        'id':              s.id,
        'name':            s.name or '',
        'code':            s.code or '',
        'specialty_id':    s.specialty_id.id if s.specialty_id else None,
        'specialty_name':  s.specialty_id.name if s.specialty_id else '',
        'visit_type':      s.visit_type or '',
        'price':           s.price,
        'insurance_price': s.insurance_price,
        'notes':           s.notes or '',
    }


class ServiceController(http.Controller):

    @http.route('/saycare/api/services', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, specialty_id='', visit_type='', **kw):
        domain = [('active', '=', True)]
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if visit_type:
            domain.append(('visit_type', '=', visit_type))
        records = request.env['saycare.service'].sudo().search(domain)
        return _json([_service_dict(s) for s in records])

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        return _json(_service_dict(s))

    @http.route('/saycare/api/services', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('name'):
            return _json({'error': 'name is required'}, 400)
        vals = {
            'name':            body['name'],
            'code':            body.get('code', ''),
            'specialty_id':    body.get('specialty_id'),
            'visit_type':      body.get('visit_type', ''),
            'price':           body.get('price', 0.0),
            'insurance_price': body.get('insurance_price', 0.0),
            'notes':           body.get('notes', ''),
        }
        rec = request.env['saycare.service'].sudo().create(vals)
        return _json(_service_dict(rec), 201)

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        allowed = ['name', 'code', 'specialty_id', 'visit_type',
                   'price', 'insurance_price', 'notes', 'active']
        vals = {k: body[k] for k in allowed if k in body}
        s.write(vals)
        return _json(_service_dict(s))

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        s.write({'active': False})
        return _json({'ok': True})
