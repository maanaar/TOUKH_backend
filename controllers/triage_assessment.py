# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json

TRIAGE_ASSESSMENT_FIELDS = [
    'received_by_nurse', 'doctor_name', 'doctor_arrival_time',
    'arrival_accompaniment', 'arrival_method',
    'call_time_1', 'call_time_2', 'call_time_3',
    'complaint_classification',
    'exam_weight', 'exam_bp', 'exam_temp', 'exam_pulse', 'exam_rr', 'exam_blood_sugar',
    'exam_color', 'exam_consciousness',
    'disposition_time', 'admitted_to', 'discharged_to',
    'leaving_consciousness', 'leaving_bp', 'leaving_pulse', 'leaving_rr',
    'leaving_temp', 'leaving_spo2', 'leaving_color',
]


def _triage_assessment_dict(a):
    return {
        'id':       a.id,
        'visit_id': a.visit_id.id,

        'received_by_nurse':   a.received_by_nurse or '',
        'doctor_name':          a.doctor_name or '',
        'doctor_arrival_time': a.doctor_arrival_time or '',

        'arrival_accompaniment': a.arrival_accompaniment or '',
        'arrival_method':         a.arrival_method or '',
        'call_time_1':            a.call_time_1 or '',
        'call_time_2':            a.call_time_2 or '',
        'call_time_3':            a.call_time_3 or '',

        'complaint_classification': a.complaint_classification or '',

        'exam_weight':       a.exam_weight or '',
        'exam_bp':             a.exam_bp or '',
        'exam_temp':           a.exam_temp or '',
        'exam_pulse':         a.exam_pulse or '',
        'exam_rr':             a.exam_rr or '',
        'exam_blood_sugar':   a.exam_blood_sugar or '',
        'exam_color':          a.exam_color or '',
        'exam_consciousness': a.exam_consciousness or '',

        'disposition_time': a.disposition_time or '',
        'admitted_to':        a.admitted_to or '',
        'discharged_to':      a.discharged_to or '',

        'leaving_consciousness': a.leaving_consciousness or '',
        'leaving_bp':              a.leaving_bp or '',
        'leaving_pulse':          a.leaving_pulse or '',
        'leaving_rr':              a.leaving_rr or '',
        'leaving_temp':            a.leaving_temp or '',
        'leaving_spo2':            a.leaving_spo2 or '',
        'leaving_color':          a.leaving_color or '',
    }


class TriageAssessmentController(http.Controller):

    def _get_or_create(self, visit_id):
        visit = request.env['saycare.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return None
        assessment = request.env['saycare.triage.assessment'].sudo().search([('visit_id', '=', visit_id)], limit=1)
        if not assessment:
            assessment = request.env['saycare.triage.assessment'].sudo().create({'visit_id': visit_id})
        return assessment

    @http.route('/saycare/api/triage-assessment/<int:visit_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, visit_id, **kw):
        assessment = self._get_or_create(visit_id)
        if assessment is None:
            return _json({'error': 'visit not found'}, 404)
        return _json(_triage_assessment_dict(assessment))

    @http.route('/saycare/api/triage-assessment/<int:visit_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, visit_id, **kw):
        assessment = self._get_or_create(visit_id)
        if assessment is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        vals = {k: body[k] for k in TRIAGE_ASSESSMENT_FIELDS if k in body}
        if vals:
            assessment.write(vals)
        return _json(_triage_assessment_dict(assessment))
