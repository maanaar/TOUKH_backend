# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
    )


def _patient_dict(p):
    return {
        'id':                p.id,
        'name':              p.name or '',
        'first_name':        p.first_name or '',
        'second_name':       p.second_name or '',
        'third_name':        p.third_name or '',
        'last_name':         p.last_name or '',
        'mrn':               p.mrn or '',
        'patient_type':      p.patient_type or 'normal',
        'id_type':           p.id_type or 'national_id',
        'id_number':         p.id_number or '',
        'dob':               str(p.dob) if p.dob else None,
        'gender':            p.gender or '',
        'mobile':            p.mobile or '',
        'home_phone':        p.home_phone or '',
        'phone':             p.phone or '',
        'occupation':        p.occupation or '',
        'nationality':       p.nationality_id.name if p.nationality_id else (p.nationality or ''),
        'governorate':       p.governorate or '',
        'city':              p.city or '',
        'street':            p.street or '',
        'financial_class':   p.financial_class or 'cash',
        'insurance_company': p.insurance_company or '',
        'contract_entity':   p.contract_entity or '',
        'image_url':         '/web/image/res.partner/%d/image_1920' % p.id if p.image_1920 else '',
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Patient search
# ─────────────────────────────────────────────────────────────────────────────

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
                ('name',       'ilike', term),
                ('mrn',        'ilike', term),
                ('id_number',  'ilike', term),
                ('mobile',     'ilike', term),
            ]

        records = request.env['res.partner'].sudo().search(domain, limit=limit)
        return _json({'patients': [_patient_dict(p) for p in records]})


# ─────────────────────────────────────────────────────────────────────────────
#  Patient CRUD
# ─────────────────────────────────────────────────────────────────────────────

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

        # Build full name from parts
        name_parts = [
            body.get('first_name', ''),
            body.get('second_name', ''),
            body.get('third_name', ''),
            body.get('last_name', ''),
        ]
        full_name = ' '.join(p for p in name_parts if p).strip()
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
            'mobile':            body.get('mobile', ''),
            'home_phone':        body.get('home_phone', ''),
            'phone':             body.get('phone', ''),
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

        # Nationality: try to resolve res.country by name
        if body.get('nationality'):
            country = request.env['res.country'].sudo().search(
                [('name', 'ilike', body['nationality'])], limit=1
            )
            if country:
                vals['nationality_id'] = country.id

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
            'mobile', 'home_phone', 'phone', 'occupation',
            'governorate', 'city', 'street', 'dob', 'gender',
            'financial_class', 'insurance_company', 'contract_entity',
        ]
        vals = {k: body[k] for k in allowed if k in body}

        # Rebuild full name if any name part changed
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
                vals['nationality_id'] = country.id

        p.write(vals)
        return _json(_patient_dict(p))


# ─────────────────────────────────────────────────────────────────────────────
#  Patient visits  (placeholder — returns empty list until visit model exists)
# ─────────────────────────────────────────────────────────────────────────────

class PatientVisitsController(http.Controller):

    @http.route('/saycare/api/patient/<int:patient_id>/visits', type='http', auth='user', methods=['GET'], csrf=False)
    def get_visits(self, patient_id, **kw):
        p = request.env['res.partner'].sudo().browse(patient_id)
        if not p.exists() or not p.is_patient:
            return _json({'error': 'patient not found'}, 404)

        # Will be replaced once saycare.visit model is created
        visits = []
        if 'saycare.visit' in request.env:
            records = request.env['saycare.visit'].sudo().search(
                [('patient_id', '=', patient_id)],
                order='admission_date desc',
            )
            for v in records:
                visits.append({
                    'id':             v.id,
                    'name':           v.name or '',
                    'admission_date': str(v.admission_date) if v.admission_date else None,
                    'discharge_date': str(v.discharge_date) if v.discharge_date else None,
                    'state':          v.state,
                    'visit_type':     v.visit_type or '',
                    'specialty':      v.specialty_id.name if v.specialty_id else '',
                    'doctor':         v.doctor_id.name if v.doctor_id else '',
                })

        return _json({'patient_id': patient_id, 'visits': visits})


# ─────────────────────────────────────────────────────────────────────────────
#  Specialties
# ─────────────────────────────────────────────────────────────────────────────

class SpecialtyController(http.Controller):

    @http.route('/saycare/api/specialties', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['saycare.specialty'].sudo().search([('active', '=', True)])
        data = [{'id': r.id, 'name': r.name, 'code': r.code or ''} for r in records]
        return _json(data)

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


# ─────────────────────────────────────────────────────────────────────────────
#  Doctors  (hr.employee where medical_role = 'doctor')
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  Nurses  (hr.employee where medical_role = 'nurse')
# ─────────────────────────────────────────────────────────────────────────────

class NurseController(http.Controller):

    @http.route('/saycare/api/nurses', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.employee'].sudo().search([
            ('medical_role', '=', 'nurse'),
            ('active', '=', True),
        ])
        data = [{
            'id':         e.id,
            'name':       e.name or '',
            'job_title':  e.job_title or '',
            'department': e.department_id.name if e.department_id else '',
            'image_url':  '/web/image/hr.employee/%d/image_1920' % e.id if e.image_1920 else '',
        } for e in records]
        return _json(data)


# ─────────────────────────────────────────────────────────────────────────────
#  Medication Orders  (saycare.medication.order)
# ─────────────────────────────────────────────────────────────────────────────

def _med_dict(m):
    return {
        'id':             m.id,
        'visit_id':       m.visit_id.id if m.visit_id else None,
        'patient_id':     m.patient_id.id if m.patient_id else None,
        'patient_name':   m.patient_id.name if m.patient_id else '',
        'product_id':     m.product_id.id if m.product_id else None,
        'product_name':   m.product_id.name if m.product_id else '',
        'drug_name':      m.drug_name or (m.product_id.name if m.product_id else ''),
        'dose':           m.dose or '',
        'frequency':      m.frequency or '',
        'duration':       m.duration or '',
        'route':          m.route or 'oral',
        'instructions':   m.instructions or '',
        'quantity':       m.quantity,
        'uom_id':         m.uom_id.id if m.uom_id else None,
        'uom_name':       m.uom_id.name if m.uom_id else '',
        'state':          m.state,
        'cancel_reason':  m.cancel_reason or '',
        'prescribed_by':  m.prescribed_by.id if m.prescribed_by else None,
        'prescribed_by_name': m.prescribed_by.name if m.prescribed_by else '',
        'prescribed_at':  str(m.prescribed_at) if m.prescribed_at else None,
        'dispensed_by':   m.dispensed_by.id if m.dispensed_by else None,
        'dispensed_by_name': m.dispensed_by.name if m.dispensed_by else '',
        'dispensed_at':   str(m.dispensed_at) if m.dispensed_at else None,
    }


class MedicationOrderController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/medications', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.medication.order'].sudo().search(
            [('visit_id', '=', visit_id)]
        )
        return _json([_med_dict(m) for m in records])

    @http.route('/saycare/api/visit/<int:visit_id>/medications', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        if not body.get('drug_name') and not body.get('product_id'):
            return _json({'error': 'drug_name or product_id is required'}, 400)

        vals = {
            'visit_id':      visit_id,
            'patient_id':    body.get('patient_id'),
            'product_id':    body.get('product_id'),
            'drug_name':     body.get('drug_name', ''),
            'dose':          body.get('dose', ''),
            'frequency':     body.get('frequency', ''),
            'duration':      body.get('duration', ''),
            'route':         body.get('route', 'oral'),
            'instructions':  body.get('instructions', ''),
            'quantity':      body.get('quantity', 1.0),
            'uom_id':        body.get('uom_id'),
            'prescribed_by': body.get('prescribed_by'),
        }
        rec = request.env['saycare.medication.order'].sudo().create(vals)
        return _json(_med_dict(rec), 201)

    @http.route('/saycare/api/visit/<int:visit_id>/medications/<int:med_id>/cancel',
                type='http', auth='user', methods=['POST'], csrf=False)
    def cancel(self, visit_id, med_id, **kw):
        med = request.env['saycare.medication.order'].sudo().browse(med_id)
        if not med.exists() or med.visit_id.id != visit_id:
            return _json({'error': 'medication order not found'}, 404)
        if med.state == 'dispensed':
            return _json({'error': 'cannot cancel a dispensed order'}, 400)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            body = {}
        med.write({'state': 'cancelled', 'cancel_reason': body.get('cancel_reason', '')})
        return _json(_med_dict(med))

    @http.route('/saycare/api/visit/<int:visit_id>/medications/<int:med_id>/dispense',
                type='http', auth='user', methods=['POST'], csrf=False)
    def dispense(self, visit_id, med_id, **kw):
        med = request.env['saycare.medication.order'].sudo().browse(med_id)
        if not med.exists() or med.visit_id.id != visit_id:
            return _json({'error': 'medication order not found'}, 404)
        if med.state != 'active':
            return _json({'error': 'only active orders can be dispensed'}, 400)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            body = {}
        from odoo.fields import Datetime as DT
        med.write({
            'state':        'dispensed',
            'dispensed_by': body.get('dispensed_by'),
            'dispensed_at': DT.now(),
        })
        return _json(_med_dict(med))


# ─────────────────────────────────────────────────────────────────────────────
#  Pharmacy queue  — all active orders across all visits
# ─────────────────────────────────────────────────────────────────────────────

class PharmacyQueueController(http.Controller):

    @http.route('/saycare/api/pharmacy/queue', type='http', auth='user', methods=['GET'], csrf=False)
    def queue(self, **kw):
        records = request.env['saycare.medication.order'].sudo().search(
            [('state', '=', 'active')],
            order='prescribed_at asc',
        )
        return _json([_med_dict(m) for m in records])
