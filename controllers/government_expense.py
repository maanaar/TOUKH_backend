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
    if 'status' in body:
        vals['status'] = body['status'] or 'جاري'
    if 'notes' in body:
        vals['notes'] = body['notes'] or ''
    if 'allowedClinics' in body:
        clinic_commands = [(5, 0, 0)]
        for clinic_data in (body['allowedClinics'] or []):
            spec_id = None
            spec_id_raw = clinic_data.get('specialtyId')
            if spec_id_raw:
                try:
                    spec = env['saycare.specialty'].browse(int(spec_id_raw))
                    if spec.exists():
                        spec_id = spec.id
                except (TypeError, ValueError):
                    pass

            service_ids = []
            product_service_ids = []
            for svc in (clinic_data.get('allowedServices') or []):
                svc_id = svc.get('id')
                source = svc.get('source', 'service')
                if not svc_id:
                    continue
                try:
                    svc_id_int = int(svc_id)
                except (TypeError, ValueError):
                    continue  # skip synthetic ids like "lab-group:blood"
                if source == 'service':
                    rec = env['saycare.service'].browse(svc_id_int)
                    if rec.exists():
                        service_ids.append(svc_id_int)
                else:
                    rec = env['product.template'].browse(svc_id_int)
                    if rec.exists():
                        product_service_ids.append(svc_id_int)

            medicine_ids = []
            for med in (clinic_data.get('allowedMedicines') or []):
                prod_id = med.get('productId') or med.get('variantId')
                if not prod_id:
                    continue
                try:
                    prod_id_int = int(prod_id)
                except (TypeError, ValueError):
                    continue
                rec = env['product.product'].browse(prod_id_int)
                if rec.exists():
                    medicine_ids.append(prod_id_int)

            clinic_commands.append((0, 0, {
                'specialty_id': spec_id,
                'specialty_name': clinic_data.get('specialtyName') or '',
                'service_ids': [(6, 0, list(dict.fromkeys(service_ids)))],
                'product_service_ids': [(6, 0, list(dict.fromkeys(product_service_ids)))],
                'medicine_ids': [(6, 0, list(dict.fromkeys(medicine_ids)))],
            }))
        vals['clinic_ids'] = clinic_commands
    if 'allocations' in body:
        vals['allocations_json'] = json.dumps(body['allocations'] or [])
    if 'allowedGroups' in body:
        vals['allowed_groups_json'] = json.dumps(body['allowedGroups'] or {})
    if 'scans' in body:
        ids = []
        for i in (body.get('scans') or []):
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass
        vals['scans_ids'] = [(6, 0, ids)]
    if 'tests' in body:
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
