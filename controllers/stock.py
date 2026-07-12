# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from .utils import _json

_logger = logging.getLogger(__name__)


class StockController(http.Controller):

    @http.route('/saycare/api/warehouses', type='http', auth='user', methods=['GET'], csrf=False)
    def get_warehouses(self, **kw):
        warehouses = request.env['stock.warehouse'].sudo().search([])
        return _json([{
            'id':   w.id,
            'name': w.name,
            'code': w.code or '',
        } for w in warehouses])

    @http.route('/saycare/api/stock', type='http', auth='user', methods=['GET'], csrf=False)
    def get_stock(self, product_product_id='', warehouse_id='', **kw):
        if not product_product_id:
            return _json({'qty': 0})
        try:
            product = request.env['product.product'].sudo().browse(int(product_product_id))
        except (ValueError, TypeError):
            return _json({'qty': 0})
        if not product.exists():
            return _json({'qty': 0})

        if warehouse_id:
            try:
                wh = request.env['stock.warehouse'].sudo().browse(int(warehouse_id))
                if wh.exists() and wh.lot_stock_id:
                    quants = request.env['stock.quant'].sudo().search([
                        ('product_id', '=', product.id),
                        ('location_id', 'child_of', wh.lot_stock_id.id),
                    ])
                    qty = sum((q.quantity - q.reserved_quantity) for q in quants)
                else:
                    qty = product.qty_available
            except Exception:
                qty = product.qty_available
        else:
            qty = product.qty_available

        return _json({'qty': float(qty)})

    @http.route('/saycare/api/stock/by-location', type='http', auth='user', methods=['GET'], csrf=False)
    def get_stock_by_location(self, location_id='', product_ids='', **kw):
        """Batch stock lookup at an arbitrary stock.location (a clinic's
        assigned موقع, which may be a whole warehouse's location or a
        narrower sub-location). Every requested product id is always present
        in the result — 0 for anything not stocked there — so callers can
        show "غير متوفر" instead of hiding the item."""
        try:
            ppids = [int(x) for x in product_ids.split(',') if x.strip().isdigit()]
        except Exception:
            ppids = []
        if not ppids:
            return _json({})

        result = {str(ppid): 0.0 for ppid in ppids}
        if not location_id:
            return _json(result)

        try:
            loc = request.env['stock.location'].sudo().browse(int(location_id))
        except (ValueError, TypeError):
            return _json(result)
        if not loc.exists():
            return _json(result)

        quants = request.env['stock.quant'].sudo().search([
            ('product_id', 'in', ppids),
            ('location_id', 'child_of', loc.id),
        ])
        for q in quants:
            result[str(q.product_id.id)] += (q.quantity - q.reserved_quantity)
        return _json(result)

    @http.route('/saycare/api/visit/<int:visit_id>/dispatch-consumables', type='http', auth='user', methods=['POST'], csrf=False)
    def dispatch_consumables(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        warehouse_id = body.get('warehouse_id')
        items        = body.get('items', [])

        if not warehouse_id:
            return _json({'error': 'warehouse_id is required'}, 400)
        if not items:
            return _json({'error': 'items list is empty'}, 400)

        env = request.env

        wh = env['stock.warehouse'].sudo().browse(int(warehouse_id))
        if not wh.exists():
            return _json({'error': 'Warehouse not found'}, 404)

        # Resolve partner from visit
        partner_id = None
        visit = env['saycare.visit'].sudo().browse(visit_id)
        if visit.exists() and visit.patient_id:
            partner_id = visit.patient_id.id

        if not partner_id:
            partner_id = env.ref('base.res_partner_1').id

        # Build sale order lines
        order_lines = []
        for item in items:
            pp_id = item.get('product_product_id')
            qty   = float(item.get('qty') or 0)
            if not pp_id or qty <= 0:
                continue
            product = env['product.product'].sudo().browse(int(pp_id))
            if not product.exists():
                continue
            uom_id = item.get('uom_id') or product.uom_id.id
            order_lines.append((0, 0, {
                'product_id':      product.id,
                'product_uom_qty': qty,
                'product_uom_id':  uom_id,
                'price_unit':      product.lst_price,
                'name':            item.get('name') or product.name,
            }))

        if not order_lines:
            return _json({'error': 'No valid items to dispatch'}, 400)

        try:
            so = env['sale.order'].sudo().create({
                'partner_id':   partner_id,
                'warehouse_id': wh.id,
                'origin':       f'Nurse Dispatch / Visit {visit_id}',
                'order_line':   order_lines,
            })
            so.action_confirm()
        except Exception as e:
            _logger.exception('dispatch-consumables: sale.order creation failed')
            return _json({'error': str(e)}, 500)

        # Validate the outgoing picking to execute the stock move
        picking = so.picking_ids[:1] if so.picking_ids else False
        picking_name = None
        if picking and picking.exists():
            picking_name = picking.name
            try:
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()
            except Exception:
                _logger.warning('dispatch-consumables: picking validation failed, leaving as ready')

        return _json({
            'sale_order_id':   so.id,
            'sale_order_name': so.name,
            'picking_id':      picking.id if picking else None,
            'picking_name':    picking_name,
        })
