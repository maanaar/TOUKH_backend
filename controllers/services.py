# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json


def _service_dict(s):
    return {
        'id':              s.id,
        'name':            s.name or '',
        'code':            s.code or '',
        'specialty_id':    s.specialty_id.id if s.specialty_id else None,
        'specialty_name':  s.specialty_id.name if s.specialty_id else '',
        'visit_type':      s.visit_type or '',
        'price':           s.price,
        'insurance_price': s.insurance_price,
        'notes':           s.notes or '',
        'source':          'service',
    }


def _product_service_dict(p, specialty_id=None, specialty_name=''):
    """Wrap a product.template that lives in a clinic's product category."""
    return {
        'id':              f'prod-{p.id}',
        'name':            p.name or '',
        'code':            p.default_code or '',
        'specialty_id':    specialty_id,
        'specialty_name':  specialty_name,
        'visit_type':      '',
        'price':           p.list_price,
        'insurance_price': 0.0,
        'notes':           '',
        'source':          'product',
    }


def _products_from_categ_keyword(env, keyword, existing_names=None):
    """Return _product_service_dict list for products in categories whose
    name contains *keyword* (case-insensitive).  Skips names already in
    existing_names to avoid duplicates."""
    if existing_names is None:
        existing_names = set()
    categs = env['product.category'].sudo().search([('name', 'ilike', keyword)])
    if not categs:
        return []
    categ_ids = env['product.category'].sudo().search(
        [('id', 'child_of', categs.ids)]
    ).ids
    products = env['product.template'].sudo().search([
        ('categ_id', 'in', categ_ids),
        ('active', '=', True),
        ('sale_ok', '=', True),
    ])
    results = []
    for p in products:
        if p.name not in existing_names:
            results.append(_product_service_dict(p))
            existing_names.add(p.name)
    return results


def _basket_items(product):
    items = []
    for item in (product.basket_table_id or []):
        sub_product = None
        sub_name    = ''
        if item.product_product_id and item.product_product_id.exists():
            sub_product = item.product_product_id
            sub_name    = sub_product.name or ''
        elif item.prod_id and item.prod_id.exists():
            tmpl        = item.prod_id
            sub_name    = tmpl.name or ''
            variants    = tmpl.product_variant_ids
            sub_product = variants[0] if variants else None
        items.append({
            'id':                 item.id,
            'serial_no':          item.serial_no or 0,
            'name':               sub_name,
            'uom':                item.uom_id.name if item.uom_id else '',
            'uom_id':             item.uom_id.id   if item.uom_id else None,
            'barcode':            item.barcode or '',
            'planned_qty':        item.planned_qty or 0,
            'price':              item.price or 0,
            'total_price':        item.total_price or 0,
            'product_product_id': sub_product.id if sub_product else None,
        })
    return items


class ServiceController(http.Controller):

    @http.route('/saycare/api/services', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, specialty_id='', visit_type='', categ_keyword='', **kw):
        env = request.env

        # ── 1. saycare.service records ────────────────────────────────────────
        # Skip generic service records when categ_keyword is the only filter
        # (lab/rad use categ_keyword without specialty_id — only category products wanted)
        results = []
        existing_names = set()
        if not (categ_keyword and not specialty_id):
            domain = [('active', '=', True)]
            if specialty_id:
                try:
                    domain.append(('specialty_id', '=', int(specialty_id)))
                except (ValueError, TypeError):
                    spec = env['saycare.specialty'].sudo().search(
                        [('name', '=', specialty_id)], limit=1
                    )
                    if spec:
                        domain.append(('specialty_id', '=', spec.id))
                    else:
                        return _json([])
            if visit_type:
                domain.append(('visit_type', '=', visit_type))
            service_records = env['saycare.service'].sudo().search(domain)
            results = [_service_dict(s) for s in service_records]
            existing_names = {r['name'] for r in results}

        # ── 1b. global saycare.service records (no specialty) ─────────────────
        # Always include services with no specialty_id when fetching for a specific specialty
        if specialty_id:
            global_svcs = env['saycare.service'].sudo().search([
                ('active', '=', True),
                ('specialty_id', '=', False),
            ])
            for s in global_svcs:
                if s.name not in existing_names:
                    results.append(_service_dict(s))
                    existing_names.add(s.name)

        # ── 2. products from the specialty's linked product category ──────────
        if specialty_id:
            try:
                spec_id = int(specialty_id)
            except (ValueError, TypeError):
                found = env['saycare.specialty'].sudo().search([('name', '=', specialty_id)], limit=1)
                spec_id = found.id if found else 0
            specialty = env['saycare.specialty'].sudo().browse(spec_id)
            if specialty.exists() and specialty.categ_id:
                categ_ids = env['product.category'].sudo().search(
                    [('id', 'child_of', specialty.categ_id.id)]
                ).ids
                products = env['product.template'].sudo().search([
                    ('categ_id', 'in', categ_ids),
                    ('active', '=', True),
                    ('sale_ok', '=', True),
                ])
                for p in products:
                    if p.name not in existing_names:
                        results.append(_product_service_dict(
                            p,
                            specialty_id=specialty.id,
                            specialty_name=specialty.name,
                        ))
                        existing_names.add(p.name)

        # ── 3. products from categories matching categ_keyword ─────────────────
        # Used by lab (keyword='تحاليل'), rad (keyword='أشعة'), clinic (keyword='عيادة')
        if categ_keyword:
            results.extend(_products_from_categ_keyword(env, categ_keyword, existing_names))

        return _json(results)

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        return _json(_service_dict(s))

    @http.route('/saycare/api/services', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('name'):
            return _json({'error': 'name is required'}, 400)
        vals = {
            'name':            body['name'],
            'code':            body.get('code', ''),
            'specialty_id':    body.get('specialty_id'),
            'visit_type':      body.get('visit_type', ''),
            'price':           body.get('price', 0.0),
            'insurance_price': body.get('insurance_price', 0.0),
            'notes':           body.get('notes', ''),
        }
        rec = request.env['saycare.service'].sudo().create(vals)
        return _json(_service_dict(rec), 201)

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        allowed = ['name', 'code', 'specialty_id', 'visit_type',
                   'price', 'insurance_price', 'notes', 'active']
        vals = {k: body[k] for k in allowed if k in body}
        s.write(vals)
        return _json(_service_dict(s))

    @http.route('/saycare/api/services/<int:service_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'error': 'service not found'}, 404)
        s.write({'active': False})
        return _json({'ok': True})

    @http.route('/saycare/api/services/<int:service_id>/basket', type='http', auth='user', methods=['GET'], csrf=False)
    def get_basket(self, service_id, **kw):
        s = request.env['saycare.service'].sudo().browse(service_id)
        if not s.exists():
            return _json({'basket': []})
        product = s.product_id
        if not product or not product.exists():
            return _json({'basket': []})
        return _json({'basket': _basket_items(product)})

    @http.route('/saycare/api/products/<int:product_id>/basket', type='http', auth='user', methods=['GET'], csrf=False)
    def get_product_basket(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return _json({'basket': []})
        return _json({'basket': _basket_items(product)})
