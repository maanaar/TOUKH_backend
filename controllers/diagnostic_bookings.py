# -*- coding: utf-8 -*-
import json
import uuid

from odoo import http
from odoo.http import request

from .lab_orders import _lab_dict
from .rad_orders import _rad_dict
from .utils import _json
from .visits import _create_visit_invoice, _visit_dict

_ALLOWED_DIAGNOSTIC_TYPES = {'lab', 'rad'}
_ALLOWED_REQUEST_SOURCES = {'reception', 'doctor', 'lab', 'external_services'}


def _patient_payload(body):
    raw = body.get('patient') if isinstance(body.get('patient'), dict) else {}
    return {
        **raw,
        **{key: body[key] for key in (
            'patient_name', 'first_name', 'second_name', 'third_name', 'last_name',
            'id_type', 'id_number', 'mrn', 'phone', 'mobile', 'home_phone',
            'patient_type', 'dob', 'gender', 'occupation', 'governorate', 'city',
            'street', 'financial_class',
        ) if key in body},
    }


def _full_name(data):
    explicit = str(data.get('name') or data.get('patient_name') or '').strip()
    if explicit:
        return explicit
    return ' '.join(
        str(data.get(key) or '').strip()
        for key in ('first_name', 'second_name', 'third_name', 'last_name')
        if str(data.get(key) or '').strip()
    )


def _resolve_patient(env, body):
    Partner = env['res.partner'].sudo()
    patient_id = body.get('patient_id')
    if patient_id:
        patient = Partner.browse(int(patient_id))
        if not patient.exists() or not patient.is_patient:
            raise ValueError('patient not found')
        return patient

    data = _patient_payload(body)
    id_number = str(data.get('id_number') or '').strip()
    mrn = str(data.get('mrn') or '').strip()

    patient = Partner
    if id_number:
        patient = Partner.search([('is_patient', '=', True), ('id_number', '=', id_number)], limit=1)
    if not patient and mrn:
        patient = Partner.search([('is_patient', '=', True), ('mrn', '=', mrn)], limit=1)
    if patient:
        return patient

    name = _full_name(data)
    if not name:
        raise ValueError('patient_id or patient name is required')

    vals = {
        'name': name,
        'is_patient': True,
        'first_name': data.get('first_name') or name,
        'second_name': data.get('second_name') or '',
        'third_name': data.get('third_name') or '',
        'last_name': data.get('last_name') or '',
        'id_type': data.get('id_type') or 'national_id',
        'id_number': id_number,
        'mrn': mrn,
        'phone': data.get('phone') or data.get('mobile') or '',
        'home_phone': data.get('home_phone') or '',
        'patient_type': data.get('patient_type') or 'normal',
        'occupation': data.get('occupation') or '',
        'governorate': data.get('governorate') or '',
        'city': data.get('city') or '',
        'street': data.get('street') or '',
        'financial_class': data.get('financial_class') or body.get('financial_class') or 'cash',
    }
    if data.get('dob'):
        vals['dob'] = data['dob']
    if data.get('gender'):
        vals['gender'] = data['gender']

    # Keep this endpoint compatible with deployments where optional patient
    # extension fields are not installed yet.
    vals = {key: value for key, value in vals.items() if key in Partner._fields}
    return Partner.create(vals)


def _normalise_services(env, body):
    raw_items = body.get('services') or body.get('orders') or []
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError('services must be a non-empty list')

    service_ids = []
    items = []
    Service = env['saycare.service'].sudo()

    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError('each service must be an object')
        raw_id = raw.get('service_id', raw.get('id'))
        try:
            service_id = int(raw_id)
        except (TypeError, ValueError):
            raise ValueError('every service requires a numeric service_id') from None

        service = Service.browse(service_id)
        if not service.exists():
            raise ValueError(f'service not found: {service_id}')
        if service_id not in service_ids:
            service_ids.append(service_id)
        items.append({
            **raw,
            'service_id': service_id,
            'name': str(raw.get('name') or service.name or '').strip(),
        })

    return service_ids, items


def _visit_vals(body, patient, diagnostic_type, request_source, service_ids):
    vals = {
        'patient_id': patient.id,
        'visit_type': 'outpatient',
        'state': 'pending_payment',
        'request_source': request_source,
        'diagnostic_type': diagnostic_type,
        'financial_class': body.get('financial_class') or getattr(patient, 'financial_class', '') or 'cash',
        'payment_method': body.get('payment_method', 'cash'),
        'notes': body.get('notes', ''),
        'created_by_name': body.get('createdByName') or request.env.user.name,
        'service_ids': [(6, 0, service_ids)],
        'decision_no': body.get('decision_no', ''),
        'expiry_date': body.get('expiry_date') or False,
        'available_balance': float(body.get('available_balance') or 0),
        'covered_services': body.get('covered_services', ''),
        'contract_entity': body.get('contract_entity', ''),
        'co_pay_percent': body.get('co_pay_percent', ''),
        'approval_required': bool(body.get('approval_required', False)),
        'admin_letter_no': body.get('admin_letter_no', ''),
        'issuing_authority': body.get('issuing_authority', ''),
        'card_number': body.get('card_number', ''),
        'financial_notes': body.get('financial_notes', ''),
        'employee_id_no': body.get('employee_id', ''),
        'department': body.get('department', ''),
    }
    return vals


class DiagnosticBookingController(http.Controller):

    @http.route('/saycare/api/diagnostic-booking', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        diagnostic_type = str(body.get('diagnostic_type') or '').strip()
        if diagnostic_type not in _ALLOWED_DIAGNOSTIC_TYPES:
            return _json({'error': 'diagnostic_type must be lab or rad'}, 400)

        request_source = str(body.get('request_source') or (
            'lab' if diagnostic_type == 'lab' else 'external_services'
        )).strip()
        if request_source not in _ALLOWED_REQUEST_SOURCES:
            return _json({'error': 'invalid request_source'}, 400)

        try:
            with request.env.cr.savepoint():
                patient = _resolve_patient(request.env, body)
                service_ids, items = _normalise_services(request.env, body)

                visit = request.env['saycare.visit'].sudo().create(
                    _visit_vals(body, patient, diagnostic_type, request_source, service_ids)
                )

                invoice_id = _create_visit_invoice(visit)
                if not invoice_id:
                    raise ValueError('invoice could not be created for diagnostic booking')
                visit.write({'invoice_id': invoice_id})

                prefix = 'LAB' if diagnostic_type == 'lab' else 'RAD'
                request_group = str(body.get('request_group') or '').strip() or (
                    f'{prefix}-{visit.id}-{uuid.uuid4().hex[:10].upper()}'
                )

                if diagnostic_type == 'lab':
                    vals_list = [{
                        'visit_id': visit.id,
                        'patient_id': patient.id,
                        'service_id': item['service_id'],
                        'request_group': request_group,
                        'test_name': item['name'],
                        'test_code': item.get('test_code', ''),
                        'priority': item.get('priority', 'routine'),
                        'notes': item.get('notes') or item.get('instructions') or body.get('clinical_notes', ''),
                        'requested_by': item.get('requested_by') or False,
                    } for item in items]
                    orders = request.env['saycare.lab.order'].sudo().create(vals_list)
                    order_payload = [_lab_dict(order) for order in orders]
                else:
                    vals_list = [{
                        'visit_id': visit.id,
                        'patient_id': patient.id,
                        'service_id': item['service_id'],
                        'request_group': request_group,
                        'study_type': item['name'],
                        'body_part': item.get('body_part', ''),
                        'clinical_indication': item.get('clinical_indication', ''),
                        'notes': item.get('notes') or item.get('instructions') or body.get('clinical_notes', ''),
                        'requested_by': item.get('requested_by') or False,
                    } for item in items]
                    orders = request.env['saycare.rad.order'].sudo().create(vals_list)
                    order_payload = [_rad_dict(order) for order in orders]

                invoice = request.env['account.move'].sudo().browse(invoice_id)
                response = {
                    'visit': _visit_dict(visit),
                    'visit_id': visit.id,
                    'patient_id': patient.id,
                    'patient_name': patient.name or '',
                    'patient_mrn': getattr(patient, 'mrn', '') or '',
                    'diagnostic_type': diagnostic_type,
                    'request_source': request_source,
                    'request_group': request_group,
                    'invoice_id': invoice_id,
                    'invoice_name': invoice.name or '',
                    'payment_state': invoice.payment_state or 'not_paid',
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'orders': order_payload,
                }
        except (TypeError, ValueError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': f'diagnostic booking failed: {exc}'}, 500)

        return _json(response, 201)
