# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json, _patient_dict


class PatientSearchController(http.Controller):

    @http.route('/saycare/api/patient/search', type='http', auth='user', methods=['GET'], csrf=False)
    def search(self, term='', limit=20, **kw):
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 20
        domain = [('is_patient', '=', True)]
        if term:
            domain += ['|', '|', '|',
                ('name',      'ilike', term),
                ('mrn',       'ilike', term),
                ('id_number', 'ilike', term),
                ('phone',     'ilike', term),
            ]
        records = request.env['res.partner'].sudo().search(domain, limit=limit)
        return _json({'patients': [_patient_dict(p) for p in records]})


class PatientController(http.Controller):

    @http.route('/saycare/api/patient/<int:patient_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, patient_id, **kw):
        p = request.env['res.partner'].sudo().browse(patient_id)
        if not p.exists() or not p.is_patient:
            return _json({'error': 'patient not found'}, 404)
        return _json(_patient_dict(p))

    @http.route('/saycare/api/patient', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        name_parts = [
            body.get('first_name', ''), body.get('second_name', ''),
            body.get('third_name', ''), body.get('last_name', ''),
        ]
        full_name = ' '.join(p for p in name_parts if p).strip() or body.get('name', '').strip()
        if not full_name:
            return _json({'error': 'patient name is required'}, 400)

        vals = {
            'name':              full_name,
            'is_patient':        True,
            'first_name':        body.get('first_name', ''),
            'second_name':       body.get('second_name', ''),
            'third_name':        body.get('third_name', ''),
            'last_name':         body.get('last_name', ''),
            'mrn':               body.get('mrn', ''),
            'patient_type':      body.get('patient_type', 'normal'),
            'id_type':           body.get('id_type', 'national_id'),
            'id_number':         body.get('id_number', ''),
            'phone':             body.get('phone', '') or body.get('mobile', ''),
            'home_phone':        body.get('home_phone', ''),
            'occupation':        body.get('occupation', ''),
            'governorate':       body.get('governorate', ''),
            'city':              body.get('city', ''),
            'street':            body.get('street', ''),
            'financial_class':   body.get('financial_class', 'cash'),
            'insurance_company': body.get('insurance_company', ''),
            'contract_entity':   body.get('contract_entity', ''),
        }
        if body.get('dob'):
            vals['dob'] = body['dob']
        if body.get('gender'):
            vals['gender'] = body['gender']
        if body.get('nationality'):
            country = request.env['res.country'].sudo().search(
                [('name', 'ilike', body['nationality'])], limit=1
            )
            if country:
                vals['country_id'] = country.id

        patient = request.env['res.partner'].sudo().create(vals)
        return _json({'id': patient.id, 'mrn': patient.mrn or '', 'name': patient.name}, 201)

    @http.route('/saycare/api/patient/<int:patient_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, patient_id, **kw):
        p = request.env['res.partner'].sudo().browse(patient_id)
        if not p.exists() or not p.is_patient:
            return _json({'error': 'patient not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        allowed = [
            'first_name', 'second_name', 'third_name', 'last_name',
            'mrn', 'patient_type', 'id_type', 'id_number',
            'phone', 'home_phone', 'occupation',
            'governorate', 'city', 'street', 'dob', 'gender',
            'financial_class', 'insurance_company', 'contract_entity',
        ]
        vals = {k: body[k] for k in allowed if k in body}
        name_parts = [
            body.get('first_name',  p.first_name  or ''),
            body.get('second_name', p.second_name or ''),
            body.get('third_name',  p.third_name  or ''),
            body.get('last_name',   p.last_name   or ''),
        ]
        full_name = ' '.join(x for x in name_parts if x).strip()
        if full_name:
            vals['name'] = full_name
        if body.get('nationality'):
            country = request.env['res.country'].sudo().search(
                [('name', 'ilike', body['nationality'])], limit=1
            )
            if country:
                vals['country_id'] = country.id
        p.write(vals)
        return _json(_patient_dict(p))


class PatientVisitsController(http.Controller):

    @http.route('/saycare/api/patient/<int:patient_id>/visits', type='http', auth='user', methods=['GET'], csrf=False)
    def get_visits(self, patient_id, **kw):
        p = request.env['res.partner'].sudo().browse(patient_id)
        if not p.exists() or not p.is_patient:
            return _json({'error': 'patient not found'}, 404)
        records = request.env['saycare.visit'].sudo().search(
            [('patient_id', '=', patient_id)], order='admission_date desc'
        )
        visits = [{
            'id':             v.id,
            'name':           v.name or '',
            'admission_date': str(v.admission_date) if v.admission_date else None,
            'state':          v.state,
            'visit_type':     v.visit_type or '',
            'specialty':      v.specialty_id.name if v.specialty_id else '',
            'doctor':         v.doctor_id.name if v.doctor_id else '',
        } for v in records]
        return _json({'patient_id': patient_id, 'visits': visits})
