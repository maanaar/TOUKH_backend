# -*- coding: utf-8 -*-
import json
import logging
from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request
from .utils import _json

_logger = logging.getLogger(__name__)

CORS = '*'


def _parse_body():
    try:
        return json.loads(request.httprequest.data or b'{}')
    except Exception:
        return {}


def _decision_vals(body, env):
    """Map JSON body to saycare.internal.decision field values."""
    vals = {}

    if 'name' in body:
        vals['name'] = body['name'] or ''
    if 'number' in body:
        vals['number'] = body['number'] or ''
    if 'startDate' in body:
        vals['start_date'] = body['startDate'] or False
    if 'durationDays' in body:
        vals['duration_days'] = int(body['durationDays'] or 90)
    if 'totalAmount' in body:
        vals['total_amount'] = float(body['totalAmount'] or 0)
    if 'deductionAmount' in body:
        vals['deduction_amount'] = max(0.0, float(body['deductionAmount'] or 0))
    if 'status' in body:
        vals['status'] = body['status'] or 'جاري'
    if 'notes' in body:
        vals['notes'] = body['notes'] or ''
    if 'createdByName' in body:
        vals['created_by_name'] = body['createdByName'] or ''
    if 'pageNo' in body and body['pageNo']:
        try:
            vals['page_no'] = int(body['pageNo'])
        except (TypeError, ValueError):
            pass

    patient = body.get('patient') or {}
    patient_id = patient.get('id')
    if patient_id:
        partner = env['res.partner'].browse(int(patient_id))
        if partner.exists():
            vals['patient_id'] = partner.id

    return vals


class InternalDecisionController(http.Controller):

    @http.route('/saycare/api/internal-decisions',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def list_decisions(self, **kw):
        env = request.env
        domain = []
        patient_id = kw.get('patient_id')
        date_from_raw = kw.get('date_from')
        date_to_raw = kw.get('date_to')
        summary_only = str(kw.get('summary') or '').lower() in ('1', 'true', 'yes')

        if patient_id:
            try:
                domain.append(('patient_id', '=', int(patient_id)))
            except (ValueError, TypeError):
                pass

        try:
            date_from = fields.Date.to_date(date_from_raw) if date_from_raw else None
            date_to = fields.Date.to_date(date_to_raw) if date_to_raw else None
        except (TypeError, ValueError):
            return _json({'error': 'صيغة التاريخ غير صحيحة'}, status=400)

        if date_from and date_to and date_from > date_to:
            return _json({'error': 'تاريخ البداية يجب أن يسبق تاريخ النهاية'}, status=400)
        if date_from:
            domain.append(('create_date', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('create_date', '<=', f'{date_to} 23:59:59'))

        records = env['saycare.internal.decision'].search(domain, order='id desc')
        serializer = '_to_list_dict' if summary_only else '_to_dict'
        return _json([getattr(record, serializer)() for record in records])

    @http.route('/saycare/api/internal-decisions/<int:decision_id>',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def get_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.internal.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        return _json(rec._to_dict())

    @http.route('/saycare/api/internal-decisions',
                type='http', auth='user', methods=['POST'], cors=CORS, csrf=False)
    def create_decision(self, **kw):
        env = request.env
        body = _parse_body()
        vals = _decision_vals(body, env)
        if not vals.get('name') or not vals.get('number'):
            return _json({'error': 'name and number are required'}, status=400)
        if not vals.get('created_by_name'):
            vals['created_by_name'] = env.user.name
        try:
            with env.cr.savepoint():
                rec = env['saycare.internal.decision'].create(vals)
        except ValidationError as e:
            return _json({'error': str(e)}, status=400)
        return _json(rec._to_dict())

    @http.route('/saycare/api/internal-decisions/<int:decision_id>',
                type='http', auth='user', methods=['PUT'], cors=CORS, csrf=False)
    def update_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.internal.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        body = _parse_body()
        vals = _decision_vals(body, env)
        if vals:
            try:
                with env.cr.savepoint():
                    rec.write(vals)
            except ValidationError as e:
                return _json({'error': str(e)}, status=400)
        return _json(rec._to_dict())

    @http.route('/saycare/api/internal-decisions/<int:decision_id>',
                type='http', auth='user', methods=['DELETE'], cors=CORS, csrf=False)
    def delete_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.internal.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        rec.unlink()
        return _json({'ok': True})

    # ── فواتير الخدمات الطبية — مرتبطة بالمريض مباشرة، مش بقرار بعينه ────────

    @http.route('/saycare/api/internal-decisions/service-invoices',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def list_service_invoices(self, **kw):
        env = request.env
        patient_id = kw.get('patient_id')
        if not patient_id:
            return _json({'error': 'patient_id is required'}, status=400)
        try:
            patient_id = int(patient_id)
        except (TypeError, ValueError):
            return _json({'error': 'patient_id must be an integer'}, status=400)
        invoices = env['saycare.internal.decision.service.invoice'].search(
            [('patient_id', '=', patient_id)]
        )
        return _json([inv._to_dict() for inv in invoices])

    @http.route('/saycare/api/internal-decisions/service-invoices',
                type='http', auth='user', methods=['POST'], cors=CORS, csrf=False)
    def add_service_invoice(self, **kw):
        env = request.env
        body = _parse_body()
        patient_id = body.get('patientId')
        if not patient_id:
            return _json({'error': 'patientId is required'}, status=400)
        try:
            patient_id = int(patient_id)
        except (TypeError, ValueError):
            return _json({'error': 'patientId must be an integer'}, status=400)
        partner = env['res.partner'].browse(patient_id)
        if not partner.exists():
            return _json({'error': 'patient not found'}, status=404)
        if not body.get('serviceName'):
            return _json({'error': 'serviceName is required'}, status=400)

        vals = {
            'patient_id': partner.id,
            'service_name': body.get('serviceName') or '',
            'amount': float(body.get('amount') or 0),
            'invoice_date': body.get('date') or fields.Date.context_today(partner),
            'notes': body.get('notes') or '',
        }
        doctor_id = body.get('doctorId')
        if doctor_id:
            try:
                vals['doctor_id'] = int(doctor_id)
            except (TypeError, ValueError):
                pass
        if body.get('doctorName'):
            vals['doctor_name'] = body.get('doctorName')
        invoice = env['saycare.internal.decision.service.invoice'].create(vals)
        return _json(invoice._to_dict())
