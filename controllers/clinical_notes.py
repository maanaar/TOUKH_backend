# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _note_dict(n):
    return {
        'id':                     n.id,
        'visit_id':               n.visit_id.id if n.visit_id else None,
        'chief_complaint':        n.chief_complaint or '',
        'complaint_duration':     n.complaint_duration or '',
        'complaint_severity':     n.complaint_severity or '',
        'associated_symptoms':    n.associated_symptoms or '',
        'nursing_notes':          n.nursing_notes or '',
        'primary_diagnosis_code': n.primary_diagnosis_code or '',
        'primary_diagnosis_desc': n.primary_diagnosis_desc or '',
        'secondary_diagnoses':    n.secondary_diagnoses or '[]',
        'differential_diagnoses': n.differential_diagnoses or '[]',
        'clinical_impression':    n.clinical_impression or '',
        'management_plan':        n.management_plan or '',
        'followup_instructions':  n.followup_instructions or '',
        'med_conditions':         n.med_conditions or '[]',
        'surgical_history':       n.surgical_history or '[]',
        'current_medications':    n.current_medications or '[]',
        'allergies':              n.allergies or '[]',
        'written_by':             n.written_by.id if n.written_by else None,
        'written_by_name':        n.written_by.name if n.written_by else '',
        'written_at':             str(n.written_at) if n.written_at else None,
    }


class ClinicalNoteController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/note', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, visit_id, **kw):
        note = request.env['saycare.clinical.note'].sudo().search(
            [('visit_id', '=', visit_id)], limit=1
        )
        return _json(_note_dict(note) if note else None)

    @http.route('/saycare/api/visit/<int:visit_id>/note', type='http', auth='user', methods=['POST'], csrf=False)
    def save(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        vals = {
            'visit_id':               visit_id,
            'chief_complaint':        body.get('chief_complaint', ''),
            'complaint_duration':     body.get('complaint_duration', ''),
            'complaint_severity':     body.get('complaint_severity', ''),
            'associated_symptoms':    body.get('associated_symptoms', ''),
            'nursing_notes':          body.get('nursing_notes', ''),
            'primary_diagnosis_code': body.get('primary_diagnosis_code', ''),
            'primary_diagnosis_desc': body.get('primary_diagnosis_desc', ''),
            'secondary_diagnoses':    json.dumps(body.get('secondary_diagnoses', [])),
            'differential_diagnoses': json.dumps(body.get('differential_diagnoses', [])),
            'clinical_impression':    body.get('clinical_impression', ''),
            'management_plan':        body.get('management_plan', ''),
            'followup_instructions':  body.get('followup_instructions', ''),
            'med_conditions':         json.dumps(body.get('med_conditions', [])),
            'surgical_history':       json.dumps(body.get('surgical_history', [])),
            'current_medications':    json.dumps(body.get('current_medications', [])),
            'allergies':              json.dumps(body.get('allergies', [])),
            'written_by':             body.get('written_by'),
        }
        existing = request.env['saycare.clinical.note'].sudo().search(
            [('visit_id', '=', visit_id)], limit=1
        )
        if existing:
            existing.write(vals)
            return _json(_note_dict(existing))
        rec = request.env['saycare.clinical.note'].sudo().create(vals)
        return _json(_note_dict(rec), 201)
