# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
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
    """Map JSON body to Odoo field values."""
    vals = {}

    if 'name' in body:
        vals['name'] = body['name'] or ''
    if 'number' in body:
        vals['number'] = body['number'] or ''
    if 'startDate' in body:
        vals['start_date'] = body['startDate'] or False
    if 'monthCount' in body:
        vals['month_count'] = int(body['monthCount'] or 3)
    if 'totalAmount' in body:
        vals['total_amount'] = float(body['totalAmount'] or 0)
    if 'deductionAmount' in body:
        vals['deduction_amount'] = max(0.0, float(body['deductionAmount'] or 0))
    if 'status' in body:
        vals['status'] = body['status'] or 'جاري'
    if 'notes' in body:
        vals['notes'] = body['notes'] or ''
    if 'allowedClinics' in body:
        spec_ids = []
        for clinic_data in (body['allowedClinics'] or []):
            spec_id_raw = clinic_data.get('specialtyId')
            if not spec_id_raw:
                continue
            try:
                spec = env['saycare.specialty'].browse(int(spec_id_raw))
                if spec.exists():
                    spec_ids.append(spec.id)
            except (TypeError, ValueError):
                pass
        vals['specialty_ids'] = [(6, 0, list(dict.fromkeys(spec_ids)))]
    if 'allocations' in body:
        vals['allocations_json'] = json.dumps(body['allocations'] or [])
        alloc_cmds = [(5, 0, 0)]
        for a in (body['allocations'] or []):
            alloc_cmds.append((0, 0, {
                'month_key': a.get('monthKey') or '',
                'label':     a.get('label') or '',
                'amount':    float(a.get('amount') or 0),
                'addition':  float(a.get('addition') or 0),
                'manual':    bool(a.get('manual', False)),
            }))
        vals['allocation_ids'] = alloc_cmds
    if 'allowedGroups' in body:
        groups = body['allowedGroups'] or {}
        vals['allowed_groups_json'] = json.dumps(groups)
        # Save medicine categories to M2M field
        med_categ_ids = []
        for item in (groups.get('medicines') or []):
            raw_id = item.get('id') if isinstance(item, dict) else item
            try:
                med_categ_ids.append(int(raw_id))
            except (TypeError, ValueError):
                pass
        vals['medicine_categ_ids'] = [(6, 0, list(dict.fromkeys(med_categ_ids)))]
        # Save labs to test_ids
        lab_ids = []
        for item in (groups.get('labs') or []):
            raw_id = item.get('id') if isinstance(item, dict) else item
            try:
                lab_ids.append(int(raw_id))
            except (TypeError, ValueError):
                pass
        vals['test_ids'] = [(6, 0, list(dict.fromkeys(lab_ids)))]
        # Save radiology to scans_ids
        rad_ids = []
        for item in (groups.get('radiology') or []):
            raw_id = item.get('id') if isinstance(item, dict) else item
            try:
                rad_ids.append(int(raw_id))
            except (TypeError, ValueError):
                pass
        vals['scans_ids'] = [(6, 0, list(dict.fromkeys(rad_ids)))]
    # 'scans' and 'tests' are category-IDs sent alongside 'allowedGroups'.
    # Only use them if allowedGroups was absent (legacy path).
    if 'scans' in body and 'allowedGroups' not in body:
        ids = []
        for i in (body.get('scans') or []):
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass
        vals['scans_ids'] = [(6, 0, ids)]
    if 'tests' in body and 'allowedGroups' not in body:
        ids = []
        for i in (body.get('tests') or []):
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass
        vals['test_ids'] = [(6, 0, ids)]

    patient = body.get('patient') or {}
    patient_id = patient.get('id')
    if patient_id:
        partner = env['res.partner'].browse(int(patient_id))
        if partner.exists():
            vals['patient_id'] = partner.id

    return vals


class GovernmentExpenseController(http.Controller):

    @http.route('/saycare/api/government-expense/decisions',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def list_decisions(self, **kw):
        env = request.env
        domain = []
        patient_id = kw.get('patient_id')
        mrn = kw.get('mrn')
        national_id = kw.get('national_id')
        if patient_id:
            try:
                domain = [('patient_id', '=', int(patient_id))]
            except (ValueError, TypeError):
                pass
        elif mrn:
            domain = [('patient_id.mrn', '=', mrn)]
        elif national_id:
            domain = [('patient_id.id_number', '=', national_id)]
        records = env['saycare.government.expense.decision'].search(domain, order='id desc')
        return _json([r._to_dict() for r in records])

    @http.route('/saycare/api/government-expense/decisions/<int:decision_id>',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def get_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.government.expense.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        return _json(rec._to_dict())

    @http.route('/saycare/api/government-expense/decisions',
                type='http', auth='user', methods=['POST'], cors=CORS, csrf=False)
    def create_decision(self, **kw):
        env = request.env
        body = _parse_body()
        vals = _decision_vals(body, env)
        if not vals.get('name') or not vals.get('number'):
            return _json({'error': 'name and number are required'}, status=400)
        rec = env['saycare.government.expense.decision'].create(vals)
        return _json(rec._to_dict())

    @http.route('/saycare/api/government-expense/decisions/<int:decision_id>',
                type='http', auth='user', methods=['PUT'], cors=CORS, csrf=False)
    def update_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.government.expense.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        body = _parse_body()
        vals = _decision_vals(body, env)
        if vals:
            rec.write(vals)
        return _json(rec._to_dict())

    @http.route('/saycare/api/government-expense/decisions/<int:decision_id>',
                type='http', auth='user', methods=['DELETE'], cors=CORS, csrf=False)
    def delete_decision(self, decision_id, **kw):
        env = request.env
        rec = env['saycare.government.expense.decision'].browse(decision_id)
        if not rec.exists():
            return _json({'error': 'not found'}, status=404)
        rec.unlink()
        return _json({'ok': True})

    @http.route('/saycare/api/government-expense/decisions/<int:decision_id>/transactions',
                type='http', auth='user', methods=['POST'], cors=CORS, csrf=False)
    def add_transaction(self, decision_id, **kw):
        env = request.env
        decision = env['saycare.government.expense.decision'].browse(decision_id)
        if not decision.exists():
            return _json({'error': 'decision not found'}, status=404)
        body = _parse_body()
        vals = {
            'decision_id': decision.id,
            'reference_no': body.get('referenceNo') or '',
            'date': body.get('date') or False,
            'item_type': body.get('itemType') or 'service',
            'specialty_id': str(body.get('specialtyId') or ''),
            'specialty_name': body.get('specialtyName') or '',
            'item_id': str(body.get('itemId') or ''),
            'item_name': body.get('itemName') or '',
            'category': body.get('category') or '',
            'amount': float(body.get('amount') or 0),
            'qty': int(body.get('qty') or 1),
            'parts_json': json.dumps(body.get('parts') or []),
            'touches_future_month': bool(body.get('touchesFutureMonth')),
            'notes': body.get('notes') or '',
        }
        txn = env['saycare.government.expense.transaction'].create(vals)
        # Return the full updated decision so frontend can sync in one shot
        return _json({'transaction': txn._to_dict(), 'decision': decision._to_dict()})

    @http.route('/saycare/api/government-expense/decisions/<int:decision_id>/transactions/<int:txn_id>',
                type='http', auth='user', methods=['DELETE'], cors=CORS, csrf=False)
    def delete_transaction(self, decision_id, txn_id, **kw):
        env = request.env
        txn = env['saycare.government.expense.transaction'].browse(txn_id)
        if not txn.exists() or txn.decision_id.id != decision_id:
            return _json({'error': 'not found'}, status=404)
        txn.unlink()
        decision = env['saycare.government.expense.decision'].browse(decision_id)
        return _json({'ok': True, 'decision': decision._to_dict() if decision.exists() else {}})

    @http.route('/saycare/api/government-expense/settings',
                type='http', auth='user', methods=['GET'], cors=CORS, csrf=False)
    def get_settings(self, **kw):
        settings = request.env['saycare.government.expense.settings'].get_settings()
        return _json(settings._to_dict())

    @http.route('/saycare/api/government-expense/settings',
                type='http', auth='user', methods=['PUT'], cors=CORS, csrf=False)
    def update_settings(self, **kw):
        body = _parse_body()
        settings = request.env['saycare.government.expense.settings'].get_settings()
        vals = {}
        if 'deductionAmount' in body:
            vals['deduction_amount'] = max(0.0, float(body['deductionAmount'] or 0))
        if 'maxAdditionAmount' in body:
            vals['max_addition_amount'] = max(0.0, float(body['maxAdditionAmount'] or 0))
        if vals:
            settings.sudo().write(vals)
        return _json(settings._to_dict())
