# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


class RefundRequestController(http.Controller):

    @http.route('/saycare/api/refund-requests', type='http', auth='user', methods=['GET'], csrf=False)
    def list_pending(self, **kw):
        records = request.env['saycare.refund.request'].sudo().search([], order='create_date desc')
        return _json([r._to_dict() for r in records])

    @http.route('/saycare/api/refund-requests', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _json({'error': 'invalid JSON'}, 400)

        visit_id = body.get('visit_id') or body.get('visitId')
        if not visit_id:
            return _json({'error': 'visit_id is required'}, 400)

        visit = request.env['saycare.visit'].sudo().browse(int(visit_id))
        if not visit.exists():
            return _json({'error': 'visit not found'}, 404)

        invoice_id = body.get('invoice_id') or body.get('invoiceId')
        vals = {
            'visit_id':     visit.id,
            'invoice_id':   int(invoice_id) if invoice_id else (visit.invoice_id.id if visit.invoice_id else False),
            'patient_id':   visit.patient_id.id if visit.patient_id else False,
            'patient_name': body.get('patient_name') or body.get('patientName') or (visit.patient_id.name if visit.patient_id else ''),
            'amount':       float(body.get('amount') or 0),
            'reason':       body.get('reason') or '',
            'source':       body.get('source') or '',
        }
        record = request.env['saycare.refund.request'].sudo().create(vals)
        return _json(record._to_dict(), 201)

    @http.route('/saycare/api/refund-requests/<int:request_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, request_id, **kw):
        record = request.env['saycare.refund.request'].sudo().browse(request_id)
        if record.exists():
            record.unlink()
        return _json({'ok': True})
