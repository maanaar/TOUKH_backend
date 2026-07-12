# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _specialty_dict(r):
    return {
        'id':          r.id,
        'name':        r.name,
        'code':        r.code or '',
        'description': r.description or '',
        'room_number': r.room_number or '',
        'categ_id':    r.categ_id.id if r.categ_id else None,
        'categ_name':  r.categ_id.name if r.categ_id else '',
        'location_id':   r.location_id.id if r.location_id else None,
        'location_name': r.location_id.complete_name if r.location_id else '',
        'doctor_ids':  [_doctor_summary(d) for d in r.doctor_ids],
        'consultant_price':           r.consultant_price or 0.0,
        'consultant_insurance_price': r.consultant_insurance_price or 0.0,
        'specialist_price':           r.specialist_price or 0.0,
        'specialist_insurance_price': r.specialist_insurance_price or 0.0,
    }


def _doctor_summary(e):
    return {
        'id':                   e.id,
        'name':                 e.name or '',
        'specialty_id':         e.specialty_id.id if e.specialty_id else None,
        'specialty_name':       e.specialty_id.name if e.specialty_id else '',
        'doctor_grade':         e.doctor_grade or '',
        'license_number':       e.license_number or '',
        'job_title':            e.job_title or '',
        'work_email':           e.work_email or '',
        'work_phone':           e.work_phone or '',
        'image_url':      '/web/image/hr.employee/%d/image_1920' % e.id if e.image_1920 else '',
    }


class SpecialtyController(http.Controller):

    @http.route('/saycare/api/specialties', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['saycare.specialty'].sudo().search([('active', '=', True)])
        return _json([_specialty_dict(r) for r in records])

    @http.route('/saycare/api/specialties', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('name'):
            return _json({'error': 'name is required'}, 400)
        vals = {
            'name':        body['name'],
            'code':        body.get('code', ''),
            'description': body.get('description', ''),
            'room_number': body.get('room_number', ''),
        }
        if body.get('categ_id'):
            vals['categ_id'] = int(body['categ_id'])
        if body.get('location_id'):
            vals['location_id'] = int(body['location_id'])
        rec = request.env['saycare.specialty'].sudo().create(vals)
        return _json(_specialty_dict(rec), 201)

    @http.route('/saycare/api/specialties/<int:spec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, spec_id, **kw):
        rec = request.env['saycare.specialty'].sudo().browse(spec_id)
        if not rec.exists():
            return _json({'error': 'specialty not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        vals = {}
        for f in ['name', 'code', 'description', 'room_number']:
            if f in body:
                vals[f] = body[f]
        if 'categ_id' in body:
            vals['categ_id'] = int(body['categ_id']) if body['categ_id'] else False
        if 'location_id' in body:
            vals['location_id'] = int(body['location_id']) if body['location_id'] else False
        if vals:
            rec.write(vals)
        return _json(_specialty_dict(rec))

    @http.route('/saycare/api/specialties/<int:spec_id>/doctors', type='http', auth='user', methods=['POST'], csrf=False)
    def assign_doctor(self, spec_id, **kw):
        """Assign an existing hr.employee (doctor) to this specialty."""
        rec = request.env['saycare.specialty'].sudo().browse(spec_id)
        if not rec.exists():
            return _json({'error': 'specialty not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        doctor_id = body.get('doctor_id')
        if not doctor_id:
            return _json({'error': 'doctor_id required'}, 400)
        emp = request.env['hr.employee'].sudo().browse(int(doctor_id))
        if not emp.exists():
            return _json({'error': 'employee not found'}, 404)
        emp.write({'specialty_id': spec_id, 'medical_role': 'doctor'})
        return _json(_specialty_dict(rec))

    @http.route('/saycare/api/specialties/<int:spec_id>/doctors/<int:doctor_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def remove_doctor(self, spec_id, doctor_id, **kw):
        """Unassign a doctor from this specialty."""
        emp = request.env['hr.employee'].sudo().browse(doctor_id)
        if emp.exists() and emp.specialty_id.id == spec_id:
            emp.write({'specialty_id': False})
        rec = request.env['saycare.specialty'].sudo().browse(spec_id)
        return _json(_specialty_dict(rec))


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
    def get_all(self, specialty='', specialty_id='', **kw):
        domain = [('medical_role', '=', 'doctor'), ('active', '=', True)]
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        elif specialty:
            domain.append(('specialty_id.name', 'ilike', specialty))
        records = request.env['hr.employee'].sudo().search(domain)
        return _json([_doctor_dict(e) for e in records])

    @http.route('/saycare/api/doctors', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('name'):
            return _json({'error': 'name is required'}, 400)
        vals = {
            'name':         body['name'],
            'medical_role': 'doctor',
            'job_title':    body.get('job_title', 'طبيب'),
            'license_number': body.get('license_number', ''),
            'work_email':   body.get('work_email', ''),
            'work_phone':   body.get('work_phone', ''),
        }
        if body.get('specialty_id'):
            vals['specialty_id'] = int(body['specialty_id'])
        if body.get('department_id'):
            vals['department_id'] = int(body['department_id'])
        emp = request.env['hr.employee'].sudo().create(vals)
        return _json(_doctor_dict(emp), 201)


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
