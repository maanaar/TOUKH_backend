# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from .utils import _json


class NotificationController(http.Controller):

    @http.route('/api/v1/notifications', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, limit='30', unread_only='', **kw):
        domain = [('user_id', '=', request.env.user.id)]
        if unread_only in ('1', 'true', 'True'):
            domain.append(('is_read', '=', False))
        limit_i = min(int(limit or 30), 100)
        recs = request.env['saycare.notification'].sudo().search(domain, limit=limit_i)
        unread_count = request.env['saycare.notification'].sudo().search_count([
            ('user_id', '=', request.env.user.id), ('is_read', '=', False),
        ])
        return _json({
            'items': [{
                'id':         r.id,
                'title':      r.title,
                'body':       r.body or '',
                'url':        r.url or '',
                'is_read':    r.is_read,
                'created_at': str(r.create_date),
            } for r in recs],
            'unread_count': unread_count,
        })

    @http.route('/api/v1/notifications/<int:rec_id>/read', type='http', auth='user', methods=['POST'], csrf=False)
    def mark_read(self, rec_id, **kw):
        rec = request.env['saycare.notification'].sudo().browse(rec_id)
        if not rec.exists() or rec.user_id.id != request.env.user.id:
            return _json({'error': 'not found'}, 404)
        rec.write({'is_read': True})
        return _json({'ok': True})

    @http.route('/api/v1/notifications/read_all', type='http', auth='user', methods=['POST'], csrf=False)
    def mark_all_read(self, **kw):
        recs = request.env['saycare.notification'].sudo().search([
            ('user_id', '=', request.env.user.id), ('is_read', '=', False),
        ])
        recs.write({'is_read': True})
        return _json({'ok': True})
