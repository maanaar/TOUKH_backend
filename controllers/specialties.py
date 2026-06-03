# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


class SpecialtyController(http.Controller):

    @http.route('/saycare/api/specialties', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['saycare.specialty'].sudo().search([('active', '=', True)])
        return _json([{
            'id':          r.id,
            'name':        r.name,
            'code':        r.code or '',
            'description': r.description or '',
            'room_number': r.room_number or '',
            'categ_id':    r.categ_id.id if r.categ_id else None,
            'categ_name':  r.categ_id.name if r.categ_id else '',
            'doctor_ids':  [{'id': d.id, 'name': d.name} for d in r.doctor_ids],
        } for r in records])

    @http.route('/saycare/api/specialties', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('name'):
            return _json({'error': 'name is required'}, 400)
        rec = request.env['saycare.specialty'].sudo().create({
            'name': body['name'],
            'code': body.get('code', ''),
        })
        return _json({'id': rec.id, 'name': rec.name, 'code': rec.code or ''}, 201)


def _doctor_dict(e):
    return {
        'id':             e.id,
        'name':           e.name or '',
        'specialty_id':   e.specialty_id.id if e.specialty_id else None,
        'specialty_name': e.specialty_id.name if e.specialty_id else '',
        'license_number': e.license_number or '',
        'job_title':      e.job_title or '',
        'department':     e.department_id.name if e.department_id else '',
        'image_url':      '/web/image/hr.employee/%d/image_1920' % e.id if e.image_1920 else '',
    }


class DoctorController(http.Controller):

    @http.route('/saycare/api/doctors', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, specialty='', **kw):
        domain = [('medical_role', '=', 'doctor'), ('active', '=', True)]
        if specialty:
            domain.append(('specialty_id.name', 'ilike', specialty))
        records = request.env['hr.employee'].sudo().search(domain)
        return _json([_doctor_dict(e) for e in records])


class NurseController(http.Controller):

    @http.route('/saycare/api/nurses', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.employee'].sudo().search([
            ('medical_role', '=', 'nurse'), ('active', '=', True),
        ])
        return _json([{
            'id':         e.id,
            'name':       e.name or '',
            'job_title':  e.job_title or '',
            'department': e.department_id.name if e.department_id else '',
            'image_url':  '/web/image/hr.employee/%d/image_1920' % e.id if e.image_1920 else '',
        } for e in records])
