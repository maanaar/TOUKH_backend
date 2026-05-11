# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


class PatientHistoryController(http.Controller):

    # ── Allergies ─────────────────────────────────────────────────────────────

    @http.route('/saycare/api/patient/<int:patient_id>/allergies', type='http', auth='user', methods=['GET'], csrf=False)
    def get_allergies(self, patient_id, **kw):
        records = request.env['saycare.patient.allergy'].sudo().search(
            [('patient_id', '=', patient_id), ('active', '=', True)]
        )
        return _json([{
            'id': r.id, 'allergen': r.allergen,
            'reaction': r.reaction or '', 'severity': r.severity,
        } for r in records])

    @http.route('/saycare/api/patient/<int:patient_id>/allergies', type='http', auth='user', methods=['POST'], csrf=False)
    def create_allergy(self, patient_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        rec = request.env['saycare.patient.allergy'].sudo().create({
            'patient_id': patient_id,
            'allergen':   body.get('allergen', ''),
            'reaction':   body.get('reaction', ''),
            'severity':   body.get('severity', 'mild'),
        })
        return _json({'id': rec.id, 'allergen': rec.allergen,
                      'reaction': rec.reaction or '', 'severity': rec.severity}, 201)

    @http.route('/saycare/api/patient/<int:patient_id>/allergies/<int:record_id>',
                type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_allergy(self, patient_id, record_id, **kw):
        rec = request.env['saycare.patient.allergy'].sudo().browse(record_id)
        if not rec.exists() or rec.patient_id.id != patient_id:
            return _json({'error': 'not found'}, 404)
        rec.write({'active': False})
        return _json({'ok': True})

    # ── Conditions ────────────────────────────────────────────────────────────

    @http.route('/saycare/api/patient/<int:patient_id>/conditions', type='http', auth='user', methods=['GET'], csrf=False)
    def get_conditions(self, patient_id, **kw):
        records = request.env['saycare.patient.condition'].sudo().search(
            [('patient_id', '=', patient_id), ('active', '=', True)]
        )
        return _json([{
            'id': r.id, 'name': r.name, 'icd_code': r.icd_code or '',
            'since_date': str(r.since_date) if r.since_date else None,
            'notes': r.notes or '',
        } for r in records])

    @http.route('/saycare/api/patient/<int:patient_id>/conditions', type='http', auth='user', methods=['POST'], csrf=False)
    def create_condition(self, patient_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        rec = request.env['saycare.patient.condition'].sudo().create({
            'patient_id': patient_id,
            'name':       body.get('name', ''),
            'icd_code':   body.get('icd_code', ''),
            'since_date': body.get('since_date'),
            'notes':      body.get('notes', ''),
        })
        return _json({'id': rec.id, 'name': rec.name}, 201)

    @http.route('/saycare/api/patient/<int:patient_id>/conditions/<int:record_id>',
                type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_condition(self, patient_id, record_id, **kw):
        rec = request.env['saycare.patient.condition'].sudo().browse(record_id)
        if not rec.exists() or rec.patient_id.id != patient_id:
            return _json({'error': 'not found'}, 404)
        rec.write({'active': False})
        return _json({'ok': True})

    # ── Surgeries ─────────────────────────────────────────────────────────────

    @http.route('/saycare/api/patient/<int:patient_id>/surgeries', type='http', auth='user', methods=['GET'], csrf=False)
    def get_surgeries(self, patient_id, **kw):
        records = request.env['saycare.patient.surgery'].sudo().search(
            [('patient_id', '=', patient_id)]
        )
        return _json([{
            'id': r.id, 'procedure_name': r.procedure_name,
            'procedure_date': str(r.procedure_date) if r.procedure_date else None,
            'hospital': r.hospital or '', 'notes': r.notes or '',
        } for r in records])

    @http.route('/saycare/api/patient/<int:patient_id>/surgeries', type='http', auth='user', methods=['POST'], csrf=False)
    def create_surgery(self, patient_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        rec = request.env['saycare.patient.surgery'].sudo().create({
            'patient_id':     patient_id,
            'procedure_name': body.get('procedure_name', ''),
            'procedure_date': body.get('procedure_date'),
            'hospital':       body.get('hospital', ''),
            'notes':          body.get('notes', ''),
        })
        return _json({'id': rec.id, 'procedure_name': rec.procedure_name}, 201)

    @http.route('/saycare/api/patient/<int:patient_id>/surgeries/<int:record_id>',
                type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_surgery(self, patient_id, record_id, **kw):
        rec = request.env['saycare.patient.surgery'].sudo().browse(record_id)
        if not rec.exists() or rec.patient_id.id != patient_id:
            return _json({'error': 'not found'}, 404)
        rec.unlink()
        return _json({'ok': True})

    # ── Current Medications ───────────────────────────────────────────────────

    @http.route('/saycare/api/patient/<int:patient_id>/medications', type='http', auth='user', methods=['GET'], csrf=False)
    def get_medications(self, patient_id, **kw):
        records = request.env['saycare.patient.medication'].sudo().search(
            [('patient_id', '=', patient_id), ('active', '=', True)]
        )
        return _json([{
            'id': r.id, 'drug_name': r.drug_name, 'dose': r.dose or '',
            'frequency': r.frequency or '',
            'start_date': str(r.start_date) if r.start_date else None,
        } for r in records])

    @http.route('/saycare/api/patient/<int:patient_id>/medications', type='http', auth='user', methods=['POST'], csrf=False)
    def create_medication(self, patient_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        rec = request.env['saycare.patient.medication'].sudo().create({
            'patient_id': patient_id,
            'drug_name':  body.get('drug_name', ''),
            'dose':       body.get('dose', ''),
            'frequency':  body.get('frequency', ''),
            'start_date': body.get('start_date'),
        })
        return _json({'id': rec.id, 'drug_name': rec.drug_name}, 201)

    @http.route('/saycare/api/patient/<int:patient_id>/medications/<int:record_id>',
                type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_medication(self, patient_id, record_id, **kw):
        rec = request.env['saycare.patient.medication'].sudo().browse(record_id)
        if not rec.exists() or rec.patient_id.id != patient_id:
            return _json({'error': 'not found'}, 404)
        rec.write({'active': False})
        return _json({'ok': True})
