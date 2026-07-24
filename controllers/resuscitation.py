# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json, _patient_dict

ICU_ROOM_TYPE = 'icu'

RESUS_FIELDS = [
    'unknown_patient', 'relative_name', 'relative_relation', 'relative_phone',
    'relative_alt_phone', 'relative_address', 'data_source', 'relative_known_info',
    'temp_name', 'temp_age', 'temp_gender',
    'airway_status', 'airway_notes',
    'breathing_status', 'breathing_notes',
    'circulation_status', 'circulation_notes',
    'disability_status', 'disability_notes',
    'exposure_status', 'exposure_notes',
    'team_lead_id', 'resus_nurse_id', 'anesthetist_status', 'required_specialty',
    'risk_o2_support', 'risk_iv_line', 'risk_ecg', 'risk_urgent_labs',
    'risk_specialist_call', 'risk_blood_prep', 'intervention_notes',
]


def _resus_vital_dict(v):
    return {
        'id':               v.id,
        'recorded_at':      str(v.recorded_at) if v.recorded_at else None,
        'blood_pressure':   v.blood_pressure or '',
        'pulse':            v.pulse,
        'temperature':      v.temperature,
        'respiratory_rate': v.respiratory_rate,
        'o2_saturation':    v.o2_saturation,
        'glucose':          v.glucose,
        'consciousness':    v.consciousness or '',
    }


def _resus_timeline_dict(t):
    return {
        'id':         t.id,
        'event_time': str(t.event_time) if t.event_time else None,
        'message':    t.message or '',
    }


def _resuscitation_dict(r, full=False):
    v = r.visit_id
    # Fall back to the bed's room when the visit's own room_id was never
    # synced (e.g. a bed was picked and saved without also assigning it).
    room = v.room_id or (v.bed_id.room_id if v.bed_id else False)
    d = {
        'id':         r.id,
        'visit_id':   v.id,
        'started_at': str(r.started_at) if r.started_at else None,

        'unknown_patient':    r.unknown_patient,
        'relative_name':      r.relative_name or '',
        'relative_relation':  r.relative_relation or '',
        'relative_phone':     r.relative_phone or '',
        'relative_alt_phone': r.relative_alt_phone or '',
        'relative_address':   r.relative_address or '',
        'data_source':        r.data_source or '',
        'relative_known_info': r.relative_known_info or '',

        'temp_name':   r.temp_name or '',
        'temp_age':    r.temp_age,
        'temp_gender': r.temp_gender or '',

        'airway_status':      r.airway_status or '',
        'airway_notes':       r.airway_notes or '',
        'breathing_status':   r.breathing_status or '',
        'breathing_notes':    r.breathing_notes or '',
        'circulation_status': r.circulation_status or '',
        'circulation_notes':  r.circulation_notes or '',
        'disability_status':  r.disability_status or '',
        'disability_notes':   r.disability_notes or '',
        'exposure_status':    r.exposure_status or '',
        'exposure_notes':     r.exposure_notes or '',

        'team_lead_id':        r.team_lead_id.id if r.team_lead_id else None,
        'team_lead_name':      r.team_lead_id.name if r.team_lead_id else '',
        'resus_nurse_id':      r.resus_nurse_id.id if r.resus_nurse_id else None,
        'resus_nurse_name':    r.resus_nurse_id.name if r.resus_nurse_id else '',
        'anesthetist_status':  r.anesthetist_status or '',
        'required_specialty':  r.required_specialty or '',

        'risk_o2_support':      r.risk_o2_support,
        'risk_iv_line':         r.risk_iv_line,
        'risk_ecg':             r.risk_ecg,
        'risk_urgent_labs':     r.risk_urgent_labs,
        'risk_specialist_call': r.risk_specialist_call,
        'risk_blood_prep':      r.risk_blood_prep,
        'intervention_notes':   r.intervention_notes or '',

        # ── visit / patient context ─────────────────────────────────────────
        'visit_name':      v.name or '',
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
    }
    if full:
        d['patient']      = _patient_dict(v.patient_id) if v.patient_id else {}
        d['vitals']       = [_resus_vital_dict(vs) for vs in r.vital_ids]
        d['timeline']     = [_resus_timeline_dict(t) for t in r.timeline_ids]
    return d


def _list_row_dict(v):
    """Lightweight row for the resuscitation queue list."""
    resus = request.env['saycare.resuscitation'].sudo().search([('visit_id', '=', v.id)], limit=1)
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
        'has_resuscitation_record': bool(resus),
        'started_at':      str(resus.started_at) if resus and resus.started_at else None,
    }


class ResuscitationListController(http.Controller):

    @http.route('/saycare/api/resuscitations', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        domain = [
            '|',
                ('room_id.room_type', '=', ICU_ROOM_TYPE),
                ('bed_id.room_id.room_type', '=', ICU_ROOM_TYPE),
            ('state', 'not in', ['cancelled']),
        ]
        records = request.env['saycare.visit'].sudo().search(domain, order='admission_date desc', limit=200)
        return _json([_list_row_dict(v) for v in records])


class ResuscitationController(http.Controller):

    def _get_or_create(self, visit_id):
        visit = request.env['saycare.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return None
        resus = request.env['saycare.resuscitation'].sudo().search([('visit_id', '=', visit_id)], limit=1)
        if not resus:
            resus = request.env['saycare.resuscitation'].sudo().create({'visit_id': visit_id})
        return resus

    @http.route('/saycare/api/resuscitation/<int:visit_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, visit_id, **kw):
        resus = self._get_or_create(visit_id)
        if resus is None:
            return _json({'error': 'visit not found'}, 404)
        return _json(_resuscitation_dict(resus, full=True))

    @http.route('/saycare/api/resuscitation/<int:visit_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, visit_id, **kw):
        resus = self._get_or_create(visit_id)
        if resus is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        vals = {k: body[k] for k in RESUS_FIELDS if k in body}
        if vals:
            resus.write(vals)
        return _json(_resuscitation_dict(resus, full=True))

    @http.route('/saycare/api/resuscitation/<int:visit_id>/vitals', type='http', auth='user', methods=['POST'], csrf=False)
    def add_vital(self, visit_id, **kw):
        resus = self._get_or_create(visit_id)
        if resus is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        def _f(val, default=0.0):
            try:
                return float(val) if val not in (None, '') else default
            except (TypeError, ValueError):
                return default

        def _i(val, default=0):
            try:
                return int(val) if val not in (None, '') else default
            except (TypeError, ValueError):
                return default

        vital = request.env['saycare.resuscitation.vital'].sudo().create({
            'resuscitation_id': resus.id,
            'blood_pressure':   body.get('blood_pressure', ''),
            'pulse':            _i(body.get('pulse')),
            'temperature':      _f(body.get('temperature')),
            'respiratory_rate': _i(body.get('respiratory_rate')),
            'o2_saturation':    _f(body.get('o2_saturation')),
            'glucose':          _f(body.get('glucose')),
            'consciousness':    body.get('consciousness', ''),
        })
        return _json(_resus_vital_dict(vital), 201)

    @http.route('/saycare/api/resuscitation/<int:visit_id>/timeline', type='http', auth='user', methods=['POST'], csrf=False)
    def add_timeline(self, visit_id, **kw):
        resus = self._get_or_create(visit_id)
        if resus is None:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        message = (body.get('message') or '').strip()
        if not message:
            return _json({'error': 'message is required'}, 400)

        entry = request.env['saycare.resuscitation.timeline'].sudo().create({
            'resuscitation_id': resus.id,
            'message':          message,
        })
        return _json(_resus_timeline_dict(entry), 201)
