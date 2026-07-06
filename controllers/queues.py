# -*- coding: utf-8 -*-
import datetime
import json as _json_mod
from odoo import http
from odoo.http import request
from .utils import _json
from .visits import _visit_dict


def _drop_refunded(records):
    """Exclude visits whose invoice has a posted refund (out_refund) against
    it - a second, independent line of defense on top of the state filter,
    in case a visit's state was never (or not yet) flipped to 'cancelled'."""
    invoice_ids = [i for i in records.mapped('invoice_id').ids if i]
    if not invoice_ids:
        return records
    refunded = request.env['account.move'].sudo().search([
        ('move_type', '=', 'out_refund'),
        ('state', '=', 'posted'),
        ('reversed_entry_id', 'in', invoice_ids),
    ])
    refunded_invoice_ids = set(refunded.mapped('reversed_entry_id').ids)
    if not refunded_invoice_ids:
        return records
    return records.filtered(
        lambda v: not v.invoice_id or v.invoice_id.id not in refunded_invoice_ids
    )


class QueueController(http.Controller):

    @http.route('/saycare/api/queue/nurse', type='http', auth='user', methods=['GET'], csrf=False)
    def nurse_queue(self, **kw):
        # Includes doctor_queue/in_progress so nurses keep visibility of a visit
        # (e.g. to dispatch a basket the doctor just ordered) after triage is done.
        records = request.env['saycare.visit'].sudo().search(
            [('state', 'in', ['waiting', 'triage', 'doctor_queue', 'in_progress'])],
            order='admission_date asc',
        )
        records = _drop_refunded(records)
        return _json([_visit_dict(v) for v in records])

    @http.route('/saycare/api/queue/doctor', type='http', auth='user', methods=['GET'], csrf=False)
    def doctor_queue(self, specialty_id='', doctor_id='', **kw):
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        # Return active visits + today's completed visits so the kanban persists after refresh
        domain = [
            '|',
            ('state', 'in', ['waiting', 'triage', 'doctor_queue', 'in_progress']),
            '&', ('state', '=', 'done'), ('admission_date', '>=', today_start),
        ]
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if doctor_id:
            domain.append(('doctor_id', '=', int(doctor_id)))
        records = request.env['saycare.visit'].sudo().search(domain, order='admission_date asc')
        records = _drop_refunded(records)
        return _json([_visit_dict(v) for v in records])

    @http.route('/saycare/api/queue/pending-basket', type='http', auth='user', methods=['GET'], csrf=False)
    def pending_basket_queue(self, **kw):
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        records = request.env['saycare.visit'].sudo().search(
            [('admission_date', '>=', today_start)],
            order='admission_date asc',
        )
        result = []
        for v in records:
            basket = _json_mod.loads(v.basket_json or '[]')
            if basket and not v.basket_paid:
                result.append(_visit_dict(v))
        return _json(result)
