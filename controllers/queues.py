# -*- coding: utf-8 -*-
import datetime
from odoo import http
from odoo.http import request
from .utils import _json
from .visits import _visit_dict


class QueueController(http.Controller):

    @http.route('/saycare/api/queue/nurse', type='http', auth='user', methods=['GET'], csrf=False)
    def nurse_queue(self, **kw):
        records = request.env['saycare.visit'].sudo().search(
            [('state', 'in', ['waiting', 'triage'])],
            order='admission_date asc',
        )
        return _json([_visit_dict(v) for v in records])

    @http.route('/saycare/api/queue/doctor', type='http', auth='user', methods=['GET'], csrf=False)
    def doctor_queue(self, specialty_id='', doctor_id='', **kw):
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        # Return active visits + today's completed visits so the kanban persists after refresh
        domain = [
            '|',
            ('state', 'in', ['doctor_queue', 'in_progress']),
            '&', ('state', '=', 'done'), ('admission_date', '>=', today_start),
        ]
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if doctor_id:
            domain.append(('doctor_id', '=', int(doctor_id)))
        records = request.env['saycare.visit'].sudo().search(domain, order='admission_date asc')
        return _json([_visit_dict(v) for v in records])
