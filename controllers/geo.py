# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from .utils import _json


class GeoController(http.Controller):

    @http.route('/saycare/api/governorates', type='http', auth='user', methods=['GET'], csrf=False)
    def list_governorates(self, **kw):
        governorates = request.env['saycare.governorate'].sudo().search([], order='sequence, name')
        return _json([
            {
                'id':      g.id,
                'name':    g.name,
                'region':  g.region or '',
                'capital': g.capital or '',
            }
            for g in governorates
        ])

    @http.route('/saycare/api/cities', type='http', auth='user', methods=['GET'], csrf=False)
    def list_cities(self, governorate_id='', **kw):
        domain = []
        if governorate_id:
            domain.append(('governorate_id', '=', int(governorate_id)))
        cities = request.env['saycare.city'].sudo().search(domain, order='governorate_id, name')
        return _json([
            {
                'id':             c.id,
                'name':           c.name,
                'governorate_id': c.governorate_id.id,
            }
            for c in cities
        ])
