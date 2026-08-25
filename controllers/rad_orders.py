# -*- coding: utf-8 -*-
import json
import uuid

from odoo import http
from odoo.fields import Datetime as DT
from odoo.http import request

from .utils import _json

RAD_VALID_TRANSITIONS = {
    'requested': ['scheduled', 'cancelled'],
    'scheduled': ['done', 'cancelled'],
    'done': [],
    'cancelled': [],
}


def _payment_state(order):
    invoice = order.visit_id.invoice_id if order.visit_id else None
    return invoice.payment_state if invoice and invoice.exists() else 'not_paid'


def _rad_dict(ro):
    payment_state = _payment_state(ro)
    return {
        'id':                  ro.id,
        'visit_id':            ro.visit_id.id if ro.visit_id else None,
        'visit_name':          ro.visit_id.name if ro.visit_id else '',
        'patient_id':          ro.patient_id.id if ro.patient_id else None,
        'patient_name':        ro.patient_id.name if ro.patient_id else '',
        'patient_mrn':         getattr(ro.patient_id, 'mrn', '') if ro.patient_id else '',
        # الرقم القومي/رقم الباسبور — حقل واحد على res.partner (id_number)
        'patient_national_id': getattr(ro.patient_id, 'id_number', '') if ro.patient_id else '',
        'service_id':          ro.service_id.id if ro.service_id else None,
        'service_name':        ro.service_id.name if ro.service_id else '',
        'product_id':          f'prod-{ro.product_id.id}' if ro.product_id else None,
        'product_name':        ro.product_id.name if ro.product_id else '',
        'request_group':       ro.request_group or '',
        'study_type':          ro.study_type or '',
        'body_part':           ro.body_part or '',
        'clinical_indication': ro.clinical_indication or '',
        'notes':               ro.notes or '',
        'state':               ro.state,
        'payment_state':       payment_state,
        'is_paid':             payment_state == 'paid',
        'invoice_id':          ro.visit_id.invoice_id.id if ro.visit_id and ro.visit_id.invoice_id else None,
        'result_notes':        ro.result_notes or '',
        'result_at':           str(ro.result_at) if ro.result_at else None,
        'requested_by':        ro.requested_by.id if ro.requested_by else None,
        'requested_by_name':   ro.requested_by.name if ro.requested_by else '',
        'requested_at':        str(ro.requested_at) if ro.requested_at else None,
    }


def _resolve_visit(visit_id):
    visit = request.env['saycare.visit'].sudo().browse(visit_id)
    return visit if visit.exists() else None


def _normalise_rad_vals(visit, body, request_group=None):
    study_type = str(body.get('study_type') or body.get('name') or '').strip()
    if not study_type:
        raise ValueError('study_type is required')

    raw_service = body.get('service_id')
    service = None
    product = None
    if isinstance(raw_service, str) and raw_service.startswith('prod-'):
        try:
            product = request.env['product.template'].sudo().browse(int(raw_service[5:]))
        except (TypeError, ValueError):
            product = None
        if not product or not product.exists():
            raise ValueError('invalid service_id')
    elif raw_service:
        try:
            service = request.env['saycare.service'].sudo().browse(int(raw_service))
        except (TypeError, ValueError):
            service = None
        if not service or not service.exists():
            raise ValueError('invalid service_id')

    return {
        'visit_id':            visit.id,
        'patient_id':          body.get('patient_id') or visit.patient_id.id,
        'service_id':          service.id if service else False,
        'product_id':          product.id if product else False,
        'request_group':       request_group or body.get('request_group') or False,
        'study_type':          study_type,
        'body_part':           body.get('body_part', ''),
        'clinical_indication': body.get('clinical_indication', ''),
        'notes':               body.get('notes', ''),
        'requested_by':        body.get('requested_by') or False,
    }


class RadOrderController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.rad.order'].sudo().search(
            [('visit_id', '=', visit_id)], order='requested_at asc, id asc'
        )
        return _json([_rad_dict(ro) for ro in records])

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        visit = _resolve_visit(visit_id)
        if not visit:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
            vals = _normalise_rad_vals(visit, body)
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)

        rec = request.env['saycare.rad.order'].sudo().create(vals)
        return _json(_rad_dict(rec), 201)

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders/bulk', type='http', auth='user', methods=['POST'], csrf=False)
    def create_bulk(self, visit_id, **kw):
        visit = _resolve_visit(visit_id)
        if not visit:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        orders = body if isinstance(body, list) else body.get('orders', [])
        if not isinstance(orders, list) or not orders:
            return _json({'error': 'orders must be a non-empty list'}, 400)

        request_group = str(
            body.get('request_group') if isinstance(body, dict) else ''
        ).strip() or f'RAD-{visit.id}-{uuid.uuid4().hex[:10].upper()}'

        try:
            vals_list = [_normalise_rad_vals(visit, item, request_group) for item in orders]
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)

        records = request.env['saycare.rad.order'].sudo().create(vals_list)
        return _json({
            'request_group': request_group,
            'visit_id': visit.id,
            'orders': [_rad_dict(rec) for rec in records],
        }, 201)

    @http.route('/saycare/api/visit/<int:visit_id>/rad-orders', type='http', auth='user', methods=['PUT'], csrf=False)
    def replace_for_visit(self, visit_id, **kw):
        """Edit a booking's selected studies before any radiology work has
        started — replaces the visit's whole saycare.rad.order set wholesale
        (these are simple line-item-like records, not stateful ones worth
        diffing individually). Refuses if any existing order for this visit
        has already moved past 'requested' (scheduled/done), since rewriting
        those would silently discard real radiology workflow progress."""
        visit = _resolve_visit(visit_id)
        if not visit:
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        orders = body.get('orders', [])
        if not isinstance(orders, list) or not orders:
            return _json({'error': 'orders must be a non-empty list'}, 400)

        existing = request.env['saycare.rad.order'].sudo().search([('visit_id', '=', visit_id)])
        in_progress = existing.filtered(lambda ro: ro.state != 'requested')
        if in_progress:
            return _json({'error': 'لا يمكن تعديل الأشعة بعد بدء التنفيذ على بعض الطلبات'}, 409)

        request_group = existing[:1].request_group or f'RAD-{visit.id}-{uuid.uuid4().hex[:10].upper()}'
        try:
            vals_list = [_normalise_rad_vals(visit, item, request_group) for item in orders]
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)

        existing.unlink()
        records = request.env['saycare.rad.order'].sudo().create(vals_list)
        return _json({
            'request_group': request_group,
            'visit_id': visit.id,
            'orders': [_rad_dict(rec) for rec in records],
        })

    @http.route('/saycare/api/rad-orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, state='', study_type='', date='', date_from='', date_to='', patient_id='', request_group='', **kw):
        domain = []
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if study_type:
            domain.append(('study_type', '=', study_type))
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
        records = request.env['saycare.rad.order'].sudo().search(
            domain, order='requested_at asc, request_group asc, id asc', limit=500
        )
        return _json([_rad_dict(ro) for ro in records])

    @http.route('/saycare/api/rad-orders/<int:order_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, order_id, **kw):
        ro = request.env['saycare.rad.order'].sudo().browse(order_id)
        if not ro.exists():
            return _json({'error': 'rad order not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        new_state = body.get('state')
        if new_state not in RAD_VALID_TRANSITIONS.get(ro.state, []):
            return _json({'error': f'cannot transition from {ro.state} to {new_state}'}, 400)
        if new_state != 'cancelled' and _payment_state(ro) != 'paid':
            return _json({'error': 'لا يمكن بدء طلب الأشعة قبل إتمام السداد'}, 409)

        vals = {'state': new_state}
        if new_state == 'done':
            vals['result_notes'] = body.get('result_notes', ro.result_notes or '')
            vals['result_at'] = DT.now()
        ro.write(vals)
        return _json(_rad_dict(ro))
