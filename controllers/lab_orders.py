# -*- coding: utf-8 -*-
import json
import uuid

from odoo import http
from odoo.fields import Datetime as DT
from odoo.http import request

from .utils import _json
from .inpatient_billing import bill_service_orders, is_admission_discharged

LAB_VALID_TRANSITIONS = {
    'requested': ['collected', 'cancelled'],
    'collected': ['resulted', 'cancelled'],
    'resulted': [],
    'cancelled': [],
}


def _payment_state(order):
    invoice = order.visit_id.invoice_id if order.visit_id else None
    return invoice.payment_state if invoice and invoice.exists() else 'not_paid'


def _lab_dict(lo):
    payment_state = _payment_state(lo)
    return {
        'id':                lo.id,
        'visit_id':          lo.visit_id.id if lo.visit_id else None,
        'visit_name':        lo.visit_id.name if lo.visit_id else '',
        'patient_id':        lo.patient_id.id if lo.patient_id else None,
        'patient_name':      lo.patient_id.name if lo.patient_id else '',
        'patient_mrn':       getattr(lo.patient_id, 'mrn', '') if lo.patient_id else '',
        'service_id':        lo.service_id.id if lo.service_id else None,
        'service_name':      lo.service_id.name if lo.service_id else '',
        'request_group':     lo.request_group or '',
        'test_name':         lo.test_name or '',
        'test_code':         lo.test_code or '',
        'priority':          lo.priority or 'routine',
        'notes':             lo.notes or '',
        'state':             lo.state,
        'payment_state':     payment_state,
        'is_paid':           payment_state == 'paid',
        'invoice_id':        lo.visit_id.invoice_id.id if lo.visit_id and lo.visit_id.invoice_id else None,
        'result_value':      lo.result_value or '',
        'result_at':         str(lo.result_at) if lo.result_at else None,
        'requested_by':      lo.requested_by.id if lo.requested_by else None,
        'requested_by_name': lo.requested_by.name if lo.requested_by else '',
        'requested_at':      str(lo.requested_at) if lo.requested_at else None,
    }


def _resolve_visit(visit_id):
    visit = request.env['saycare.visit'].sudo().browse(visit_id)
    return visit if visit.exists() else None


def _normalise_lab_vals(visit, body, request_group=None):
    test_name = str(body.get('test_name') or body.get('name') or '').strip()
    if not test_name:
        raise ValueError('test_name is required')

    service_id = body.get('service_id')
    service = request.env['saycare.service'].sudo().browse(int(service_id)) if service_id else None
    if service_id and (not service or not service.exists()):
        raise ValueError('invalid service_id')

    return {
        'visit_id':     visit.id,
        'patient_id':   body.get('patient_id') or visit.patient_id.id,
        'service_id':   service.id if service and service.exists() else False,
        'request_group': request_group or body.get('request_group') or False,
        'test_name':    test_name,
        'test_code':    body.get('test_code', ''),
        'priority':     body.get('priority', 'routine'),
        'notes':        body.get('notes', ''),
        'requested_by': body.get('requested_by') or False,
    }


class LabOrderController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.lab.order'].sudo().search(
            [('visit_id', '=', visit_id)], order='requested_at asc, id asc'
        )
        return _json([_lab_dict(lo) for lo in records])

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        visit = _resolve_visit(visit_id)
        if not visit:
            return _json({'error': 'visit not found'}, 404)
        if is_admission_discharged(visit):
            return _json({'error': 'تم إغلاق فاتورة هذا المريض بعد الخروج — لا يمكن إضافة طلبات جديدة'}, 400)
        try:
            body = json.loads(request.httprequest.data or '{}')
            vals = _normalise_lab_vals(visit, body)
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)

        rec = request.env['saycare.lab.order'].sudo().create(vals)
        bill_service_orders(visit, rec)
        return _json(_lab_dict(rec), 201)

    @http.route('/saycare/api/visit/<int:visit_id>/lab-orders/bulk', type='http', auth='user', methods=['POST'], csrf=False)
    def create_bulk(self, visit_id, **kw):
        visit = _resolve_visit(visit_id)
        if not visit:
            return _json({'error': 'visit not found'}, 404)
        if is_admission_discharged(visit):
            return _json({'error': 'تم إغلاق فاتورة هذا المريض بعد الخروج — لا يمكن إضافة طلبات جديدة'}, 400)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        orders = body if isinstance(body, list) else body.get('orders', [])
        if not isinstance(orders, list) or not orders:
            return _json({'error': 'orders must be a non-empty list'}, 400)

        request_group = str(
            body.get('request_group') if isinstance(body, dict) else ''
        ).strip() or f'LAB-{visit.id}-{uuid.uuid4().hex[:10].upper()}'

        try:
            vals_list = [_normalise_lab_vals(visit, item, request_group) for item in orders]
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)

        records = request.env['saycare.lab.order'].sudo().create(vals_list)
        bill_service_orders(visit, records)
        return _json({
            'request_group': request_group,
            'visit_id': visit.id,
            'orders': [_lab_dict(rec) for rec in records],
        }, 201)

    @http.route('/saycare/api/lab-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, state='', priority='', date='', date_from='', date_to='', patient_id='', request_group='', **kw):
        domain = []
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if priority:
            domain.append(('priority', '=', priority))
        if request_group:
            domain.append(('request_group', '=', request_group))
        if date_from or date_to:
            if date_from:
                domain.append(('requested_at', '>=', f'{date_from} 00:00:00'))
            if date_to:
                domain.append(('requested_at', '<=', f'{date_to} 23:59:59'))
        elif date:
            domain += [
                ('requested_at', '>=', f'{date} 00:00:00'),
                ('requested_at', '<=', f'{date} 23:59:59'),
            ]
        if patient_id:
            try:
                domain.append(('patient_id', '=', int(patient_id)))
            except (ValueError, TypeError):
                pass
        records = request.env['saycare.lab.order'].sudo().search(
            domain, order='requested_at asc, request_group asc, id asc', limit=500
        )
        return _json([_lab_dict(lo) for lo in records])

    @http.route('/saycare/api/lab-orders/<int:order_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, order_id, **kw):
        lo = request.env['saycare.lab.order'].sudo().browse(order_id)
        if not lo.exists():
            return _json({'error': 'lab order not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        new_state = body.get('state')
        if new_state not in LAB_VALID_TRANSITIONS.get(lo.state, []):
            return _json({'error': f'cannot transition from {lo.state} to {new_state}'}, 400)
        if new_state != 'cancelled' and _payment_state(lo) != 'paid':
            return _json({'error': 'لا يمكن بدء طلب التحليل قبل إتمام السداد'}, 409)

        vals = {'state': new_state}
        if new_state == 'resulted':
            vals['result_value'] = body.get('result_value', lo.result_value or '')
            vals['result_at'] = DT.now()
        lo.write(vals)
        return _json(_lab_dict(lo))
