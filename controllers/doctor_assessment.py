# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json, _patient_dict

ASSESSMENT_FIELDS = [
    'chief_complaint', 'history_present_illness',
    'general_appearance', 'neuro_status',
    'chest_findings', 'heart_findings', 'abdomen_findings', 'limbs_findings', 'exam_notes',
    'sample_signs_symptoms', 'sample_allergies', 'sample_medications',
    'sample_past_history', 'sample_last_intake', 'sample_events',
    'requested_tests_notes', 'requested_procedures_notes',
    'diagnosis', 'treatment_plan', 'treatment_given', 'consultant_id', 'medical_advice',
    'case_exit',

    # ── مرفقات طبية — نموذج كشف قسم الطوارئ الورقي ──────────────────────────────
    'sheet_no', 'sheet_visit_type', 'sheet_referral_party',
    'sheet_type', 'sheet_age', 'sheet_patient_card_no', 'sheet_address',
    'sheet_phone', 'sheet_arrival_desc', 'sheet_date', 'sheet_arrival_time',
    'sheet_card_no', 'sheet_companion', 'sheet_departure_time', 'sheet_patient_name',
    'sheet_vs_pulse', 'sheet_vs_temp', 'sheet_vs_bp', 'sheet_vs_rr', 'sheet_vs_allergies',
    'sheet_main_complaint', 'sheet_physical_findings', 'sheet_investigation_ordered',
    'sheet_procedure_done', 'sheet_diagnosis', 'sheet_treatment', 'sheet_consultant',
    'sheet_advice_action', 'sheet_nurse_sign', 'sheet_doctor_sign', 'sheet_cod',
]


def _request_dict(r):
    return {'id': r.id, 'name': r.name or ''}


def _assessment_dict(a, full=False):
    v = a.visit_id
    room = v.room_id or (v.bed_id.room_id if v.bed_id else False)

    # Prefer data captured during resuscitation (more recent / critical) over
    # the original triage-time values, falling back to triage when the
    # patient never went through resuscitation or a field wasn't recorded.
    resus = request.env['saycare.resuscitation'].sudo().search([('visit_id', '=', v.id)], limit=1)
    consciousness_level = (resus.disability_status if resus and resus.disability_status else v.consciousness_level) or ''
    last_blood_pressure = resus.vital_ids[:1].blood_pressure if resus and resus.vital_ids else ''
    if not last_blood_pressure:
        last_vital = v.vital_sign_ids[:1]
        last_blood_pressure = last_vital.blood_pressure if last_vital else ''

    d = {
        'id':       a.id,
        'visit_id': v.id,

        'chief_complaint':         a.chief_complaint or '',
        'history_present_illness': a.history_present_illness or '',

        'general_appearance': a.general_appearance or '',
        'neuro_status':       a.neuro_status or '',
        'chest_findings':     a.chest_findings or '',
        'heart_findings':     a.heart_findings or '',
        'abdomen_findings':   a.abdomen_findings or '',
        'limbs_findings':     a.limbs_findings or '',
        'exam_notes':         a.exam_notes or '',

        'sample_signs_symptoms': a.sample_signs_symptoms or '',
        'sample_allergies':      a.sample_allergies or '',
        'sample_medications':    a.sample_medications or '',
        'sample_past_history':   a.sample_past_history or '',
        'sample_last_intake':    a.sample_last_intake or '',
        'sample_events':         a.sample_events or '',

        'requested_tests_notes':      a.requested_tests_notes or '',
        'requested_procedures_notes': a.requested_procedures_notes or '',

        'diagnosis':        a.diagnosis or '',
        'treatment_plan':   a.treatment_plan or '',
        'treatment_given':  a.treatment_given or '',
        'consultant_id':    a.consultant_id.id if a.consultant_id else None,
        'consultant_name':  a.consultant_id.name if a.consultant_id else '',
        'medical_advice':   a.medical_advice or '',
        'case_exit':        a.case_exit or '',

        'sheet_no':                    a.sheet_no or '',
        'sheet_visit_type':            a.sheet_visit_type or '',
        'sheet_referral_party':        a.sheet_referral_party or '',
        'sheet_type':                  a.sheet_type or '',
        'sheet_age':                   a.sheet_age or '',
        'sheet_patient_card_no':       a.sheet_patient_card_no or '',
        'sheet_address':               a.sheet_address or '',
        'sheet_phone':                 a.sheet_phone or '',
        'sheet_arrival_desc':          a.sheet_arrival_desc or '',
        'sheet_date':                  str(a.sheet_date) if a.sheet_date else None,
        'sheet_arrival_time':          a.sheet_arrival_time or '',
        'sheet_card_no':               a.sheet_card_no or '',
        'sheet_companion':             a.sheet_companion or '',
        'sheet_departure_time':        a.sheet_departure_time or '',
        'sheet_patient_name':          a.sheet_patient_name or '',
        'sheet_vs_pulse':              a.sheet_vs_pulse or '',
        'sheet_vs_temp':               a.sheet_vs_temp or '',
        'sheet_vs_bp':                 a.sheet_vs_bp or '',
        'sheet_vs_rr':                 a.sheet_vs_rr or '',
        'sheet_vs_allergies':          a.sheet_vs_allergies or '',
        'sheet_main_complaint':        a.sheet_main_complaint or '',
        'sheet_physical_findings':     a.sheet_physical_findings or '',
        'sheet_investigation_ordered': a.sheet_investigation_ordered or '',
        'sheet_procedure_done':        a.sheet_procedure_done or '',
        'sheet_diagnosis':             a.sheet_diagnosis or '',
        'sheet_treatment':             a.sheet_treatment or '',
        'sheet_consultant':            a.sheet_consultant or '',
        'sheet_advice_action':         a.sheet_advice_action or '',
        'sheet_nurse_sign':            a.sheet_nurse_sign or '',
        'sheet_doctor_sign':           a.sheet_doctor_sign or '',
        'sheet_cod':                   a.sheet_cod or '',

        # ── visit / patient context ─────────────────────────────────────────
        'visit_name':          v.name or '',
        'state':               v.state,
        'triage_color':        v.triage_color or '',
        'consciousness_level': consciousness_level,
        'skin_color':          v.skin_color or '',
        'allergy_status':      v.allergy_status or '',
        'last_blood_pressure': last_blood_pressure,
        'admission_date':  str(v.admission_date) if v.admission_date else None,
        'room_id':         room.id if room else None,
        'room_name':       room.room_no if room else '',
        'bed_id':          v.bed_id.id if v.bed_id else None,
        'bed_name':        v.bed_id.code if v.bed_id else '',
        'patient_id':      v.patient_id.id if v.patient_id else None,
        'patient_name':    v.patient_id.name if v.patient_id else '',
        'patient_mrn':     getattr(v.patient_id, 'mrn', '') if v.patient_id else '',
        'companion_name':  v.companion_name or '',
    }
    if full:
        d['patient']  = _patient_dict(v.patient_id) if v.patient_id else {}
        d['requests'] = [_request_dict(r) for r in a.request_ids]
    return d


def _list_row_dict(v):
    assessment = request.env['saycare.doctor.assessment'].sudo().search([('visit_id', '=', v.id)], limit=1)
    room = v.room_id or (v.bed_id.room_id if v.bed_id else False)
    return {
        'id':              v.id,
        'name':            v.name or '',
        'state':           v.state,
        'triage_color':    v.triage_color or '',
        'chief_complaint': v.chief_complaint or '',
        'admission_date':  str(v.admission_date) if v.admission_date else None,
        'room_id':         room.id if room else None,
        'room_name':       room.room_no if room else '',
        'bed_id':          v.bed_id.id if v.bed_id else None,
        'bed_name':        v.bed_id.code if v.bed_id else '',
        'patient_id':      v.patient_id.id if v.patient_id else None,
        'patient_name':    v.patient_id.name if v.patient_id else '',
        'patient_mrn':     getattr(v.patient_id, 'mrn', '') if v.patient_id else '',
        'has_assessment_record': bool(assessment),
    }


class DoctorAssessmentListController(http.Controller):

    @http.route('/saycare/api/doctor-assessments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        domain = [('visit_type', '=', 'emergency'), ('state', '=', 'doctor_queue')]
        records = request.env['saycare.visit'].sudo().search(domain, order='admission_date desc', limit=200)
        return _json([_list_row_dict(v) for v in records])


class DoctorAssessmentController(http.Controller):

    def _get_or_create(self, visit_id):
        visit = request.env['saycare.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return None
        assessment = request.env['saycare.doctor.assessment'].sudo().search([('visit_id', '=', visit_id)], limit=1)
        if not assessment:
            assessment = request.env['saycare.doctor.assessment'].sudo().create({
                'visit_id':         visit_id,
                'chief_complaint':  visit.chief_complaint or '',
            })
        return assessment

    @http.route('/saycare/api/doctor-assessment/<int:visit_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, visit_id, **kw):
        assessment = self._get_or_create(visit_id)
        if assessment is None:
            return _json({'error': 'visit not found'}, 404)
        return _json(_assessment_dict(assessment, full=True))

    @http.route('/saycare/api/doctor-assessment/<int:visit_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, visit_id, **kw):
        assessment = self._get_or_create(visit_id)
        if assessment is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        vals = {k: body[k] for k in ASSESSMENT_FIELDS if k in body}
        if vals:
            assessment.write(vals)
        return _json(_assessment_dict(assessment, full=True))

    @http.route('/saycare/api/doctor-assessment/<int:visit_id>/requests', type='http', auth='user', methods=['POST'], csrf=False)
    def add_request(self, visit_id, **kw):
        assessment = self._get_or_create(visit_id)
        if assessment is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        name = (body.get('name') or '').strip()
        if not name:
            return _json({'error': 'name is required'}, 400)

        req = request.env['saycare.doctor.assessment.request'].sudo().create({
            'assessment_id': assessment.id,
            'name':          name,
        })
        return _json(_request_dict(req), 201)

    @http.route('/saycare/api/doctor-assessment/<int:visit_id>/requests/<int:request_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_request(self, visit_id, request_id, **kw):
        req = request.env['saycare.doctor.assessment.request'].sudo().browse(request_id)
        if not req.exists() or req.assessment_id.visit_id.id != visit_id:
            return _json({'error': 'request not found'}, 404)
        req.unlink()
        return _json({'deleted': True, 'id': request_id})
