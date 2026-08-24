# -*- coding: utf-8 -*-
import datetime
import json as _json_mod
from odoo import http
from odoo.http import request
from odoo.osv import expression
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
    def nurse_queue(self, date='', date_from='', date_to='', **kw):
        # doctor_queue/in_progress stay visible regardless of date so nurses
        # keep visibility of a visit (e.g. to dispatch a basket the doctor just
        # ordered) after triage is done, even if it was admitted on a prior day.
        # waiting/triage are scoped to the requested day when given — without
        # this, every visit ever created in those states (unbounded, no date
        # restriction) was fetched and shipped to the browser on every poll.
        #
        # admission_date is stored in UTC. `date_from`/`date_to` are exact UTC
        # instants the caller computed from the *browser's local* calendar day
        # (so "today" lines up with the nurse's actual local today regardless
        # of timezone offset). The bare `date` param is kept only as a coarser
        # fallback for other/older callers and is matched as a naive UTC day.
        carryover_domain = [('state', 'in', ['doctor_queue', 'in_progress'])]
        todays_domain = [('state', 'in', ['waiting', 'triage'])]
        if date_from or date_to:
            if date_from:
                todays_domain.append(('admission_date', '>=', date_from))
            if date_to:
                todays_domain.append(('admission_date', '<=', date_to))
            domain = expression.OR([todays_domain, carryover_domain])
        elif date:
            todays_domain += [
                ('admission_date', '>=', f'{date} 00:00:00'),
                ('admission_date', '<=', f'{date} 23:59:59'),
            ]
            domain = expression.OR([todays_domain, carryover_domain])
        else:
            domain = expression.OR([todays_domain, carryover_domain])
        records = request.env['saycare.visit'].sudo().search(domain, order='admission_date asc')
        records = _drop_refunded(records)
        return _json([_visit_dict(v) for v in records])

    @http.route('/saycare/api/queue/doctor', type='http', auth='user', methods=['GET'], csrf=False)
    def doctor_queue(self, specialty_id='', doctor_id='', **kw):
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        # Return active visits + today's completed visits so the kanban persists after refresh.
        # visit_type != 'emergency': طبيب العيادات only - emergency cases route
        # through الفرز (nurse_queue, filtered client-side in TriagePage.jsx)
        # instead, so they must never surface here regardless of state.
        domain = [
            ('visit_type', '!=', 'emergency'),
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
