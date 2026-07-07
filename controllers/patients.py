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

        def sel(key, default, valid):
            v = body.get(key) or default
            return v if v in valid else default

        pf = request.env['res.partner']._fields  # available fields

        # Always-safe standard Odoo fields
        vals = {
            'name':   full_name,
            'phone':  body.get('phone', '') or body.get('mobile', '') or '',
            'city':   body.get('city', '') or '',
            'street': body.get('street', '') or '',
        }

        # Custom saycare fields — only add if they exist in this database
        custom = {
            'is_patient':        True,
            'first_name':        body.get('first_name', '') or '',
            'second_name':       body.get('second_name', '') or '',
            'third_name':        body.get('third_name', '') or '',
            'last_name':         body.get('last_name', '') or '',
            'patient_type':      sel('patient_type', 'normal', ('normal', 'foreigner', 'unknown', 'baby')),
            'id_type':           sel('id_type', 'national_id', ('national_id', 'passport')),
            'id_number':         body.get('id_number', '') or '',
            'home_phone':        body.get('home_phone', '') or '',
            'occupation':        body.get('occupation', '') or '',
            'governorate':       body.get('governorate', '') or '',
            'financial_class':   sel('financial_class', 'cash',
                                     ('cash', 'state', 'consultation', 'takaful', 'insurance', 'contract', 'moh', 'staff')),
            'insurance_company': body.get('insurance_company', '') or '',
            'contract_entity':   body.get('contract_entity', '') or '',
            'x_blood_type':      sel('blood_type', False,
                                     ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
            'entry_permit_no':   body.get('entry_permit_no', '') or '',
        }
        for k, v in custom.items():
            if k in pf:
                vals[k] = v

        # entry_permit_no = (body.get('entry_permit_no') or '').strip()
        # if entry_permit_no and not entry_permit_no.isdigit():
        #     return _json({'error': 'إذن الدخول يجب أن يحتوي على أرقام فقط'}, 400)

        dob = body.get('dob')
        if dob and 'dob' in pf:
            vals['dob'] = dob
        gender = body.get('gender')
        if gender in ('male', 'female') and 'gender' in pf:
            vals['gender'] = gender
        if body.get('nationality'):
            country = request.env['res.country'].sudo().search(
                [('name', 'ilike', body['nationality'])], limit=1
            )
            if country:
                vals['country_id'] = country.id

        # ── duplication guard: match by id_number or mrn ─────────────────────
        id_number = body.get('id_number', '').strip()
        mrn       = body.get('mrn', '').strip()
        existing  = None
        # Guard against missing custom fields (module not yet upgraded)
        partner_fields = request.env['res.partner']._fields
        try:
            if id_number and 'id_number' in partner_fields:
                existing = request.env['res.partner'].sudo().search([
                    ('is_patient', '=', True), ('id_number', '=', id_number),
                ], limit=1)
            if not existing and mrn and 'mrn' in partner_fields:
                existing = request.env['res.partner'].sudo().search([
                    ('is_patient', '=', True), ('mrn', '=', mrn),
                ], limit=1)
        except Exception:
            existing = None

        if entry_permit_no:
            dup_domain = [('entry_permit_no', '=', entry_permit_no)]
            if existing:
                dup_domain.append(('id', '!=', existing.id))
            if request.env['res.partner'].sudo().search_count(dup_domain):
                return _json({'error': 'رقم إذن الدخول مستخدم من قبل، برجاء إدخال رقم آخر.'}, 409)

        try:
            if existing:
                existing.write(vals)
                return _json({
                    'id': existing.id, 'mrn': getattr(existing, 'mrn', '') or '', 'name': existing.name,
                    'entry_permit_no': getattr(existing, 'entry_permit_no', '') or '',
                }, 200)

            patient = request.env['res.partner'].sudo().create(vals)
            return _json({
                'id': patient.id, 'mrn': getattr(patient, 'mrn', '') or '', 'name': patient.name,
                'entry_permit_no': getattr(patient, 'entry_permit_no', '') or '',
            }, 201)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error('Patient create/write failed: %s', e, exc_info=True)
            request.env.cr.rollback()
            # Fallback: create with minimal safe fields if custom fields are missing
            try:
                safe_vals = {
                    'name':  full_name,
                    'phone': body.get('phone', '') or body.get('mobile', ''),
                    'city':  body.get('city', '') or '',
                    'street': body.get('street', '') or '',
                }
                patient = request.env['res.partner'].sudo().create(safe_vals)
                return _json({'id': patient.id, 'mrn': '', 'name': patient.name}, 201)
            except Exception as e2:
                return _json({'error': str(e2)}, 500)

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
            'x_blood_type', 'entry_permit_no',
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

        # entry_permit_no = (vals.get('entry_permit_no') or '').strip()
        # if entry_permit_no:
        #     if not entry_permit_no.isdigit():
        #         return _json({'error': 'إذن الدخول يجب أن يحتوي على أرقام فقط'}, 400)
        #     if request.env['res.partner'].sudo().search_count([
        #         ('entry_permit_no', '=', entry_permit_no), ('id', '!=', p.id),
        #     ]):
        #         return _json({'error': 'رقم إذن الدخول مستخدم من قبل، برجاء إدخال رقم آخر.'}, 409)

        p.write(vals)
        return _json(_patient_dict(p))


class InsuranceProviderController(http.Controller):

    @http.route('/saycare/api/insurance-providers', type='http', auth='user', methods=['GET'], csrf=False)
    def list_providers(self, provider_type='', **kw):
        domain = [('provider_type', '=', provider_type)] if provider_type else []
        records = request.env['insurance.company'].sudo().search(domain, order='name asc')
        return _json({'providers': [{'id': r.id, 'name': r.name} for r in records]})


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
