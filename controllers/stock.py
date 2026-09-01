# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from .utils import _json
from .inpatient_billing import add_bill_line

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

    @http.route('/saycare/api/stock/transfer-item-details', type='http', auth='user', methods=['GET'], csrf=False)
    def get_transfer_item_details(self, location_id='', product_ids='', **kw):
        """Per-product stock snapshot at a source location for شاشة طلبات صرف
        واستلام الأقسام's "الأصناف المطلوبة" table: quantity available there
        right now, plus the nearest-to-expire lot/serial (FEFO) — so whoever
        is preparing the transfer sees what they'd actually be sending before
        they confirm quantities. product_ids are product.template ids (this
        screen's product picker returns templates, not variants — same as
        PickingCreateController.create_picking's product_id resolution)."""
        try:
            tmpl_ids = [int(x) for x in product_ids.split(',') if x.strip().isdigit()]
        except Exception:
            tmpl_ids = []

        result = {str(tid): {
            'qty_available':   0.0,
            'lot_id':          None,
            'lot_name':        None,
            'expiration_date': None,
        } for tid in tmpl_ids}
        if not tmpl_ids or not location_id:
            return _json(result)

        try:
            loc = request.env['stock.location'].sudo().browse(int(location_id))
        except (ValueError, TypeError):
            return _json(result)
        if not loc.exists():
            return _json(result)

        variants = request.env['product.product'].sudo().search([('product_tmpl_id', 'in', tmpl_ids)])
        if not variants:
            return _json(result)
        variant_to_tmpl = {v.id: v.product_tmpl_id.id for v in variants}

        quants = request.env['stock.quant'].sudo().search([
            ('product_id', 'in', variants.ids),
            ('location_id', 'child_of', loc.id),
        ])

        best_lot = {}
        for q in quants:
            tid = variant_to_tmpl.get(q.product_id.id)
            if tid is None:
                continue
            result[str(tid)]['qty_available'] += (q.quantity - q.reserved_quantity)
            if q.lot_id:
                # expiration_date only exists on stock.lot when the product_expiry
                # module is installed — getattr keeps this endpoint working (just
                # without an expiry value) on installs that don't have it enabled.
                exp = getattr(q.lot_id, 'expiration_date', False)
                current = best_lot.get(tid)
                if current is None or (
                    exp and (not getattr(current.lot_id, 'expiration_date', False) or exp < current.lot_id.expiration_date)
                ):
                    best_lot[tid] = q

        for tid, q in best_lot.items():
            exp = getattr(q.lot_id, 'expiration_date', False)
            result[str(tid)]['lot_id']          = q.lot_id.id
            result[str(tid)]['lot_name']        = q.lot_id.name
            result[str(tid)]['expiration_date'] = str(exp.date()) if exp else None

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

        # Inpatient visits bill onto the admission's single running Open Bill
        # (saycare.admission.request.sale_order_id) instead of a one-off order
        # per dispatch — stock still has to leave the shelf immediately, so
        # each item still gets its own validated stock.move right away, just
        # linked to that shared order's lines via sale_line_id (see
        # inpatient_billing.add_bill_line) rather than via a separate order.
        admission = None
        if visit.exists() and visit.visit_type == 'inpatient':
            admission = env['saycare.admission.request'].sudo().search(
                [('visit_id', '=', visit_id)], limit=1
            )
            if admission and admission.worklist_stage == 'discharged':
                return _json({'error': 'تم إغلاق فاتورة هذا المريض بعد الخروج — لا يمكن إضافة أصناف جديدة'}, 400)

        # Build item list (resolved products)
        resolved_items = []
        for item in items:
            pp_id = item.get('product_product_id')
            qty   = float(item.get('qty') or 0)
            if not pp_id or qty <= 0:
                continue
            product = env['product.product'].sudo().browse(int(pp_id))
            if not product.exists():
                continue
            resolved_items.append((product, qty, item.get('name') or product.name))

        if not resolved_items:
            return _json({'error': 'No valid items to dispatch'}, 400)

        if admission:
            try:
                for product, qty, name in resolved_items:
                    add_bill_line(admission, product, qty, product.lst_price, name,
                                  warehouse=wh, deliver_now=True)
                so = admission.sale_order_id
            except Exception as e:
                _logger.exception('dispatch-consumables: inpatient open-bill dispatch failed')
                return _json({'error': str(e)}, 500)

            return _json({
                'sale_order_id':   so.id,
                'sale_order_name': so.name,
                'picking_id':      None,
                'picking_name':    None,
            })

        # Outpatient / no admission record: previous one-off-order-per-dispatch behavior.
        order_lines = [(0, 0, {
            'product_id':      product.id,
            'product_uom_qty': qty,
            'product_uom_id':  product.uom_id.id,
            'price_unit':      product.lst_price,
            'name':            name,
        }) for product, qty, name in resolved_items]

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

    @http.route('/saycare/api/visit/<int:visit_id>/dispensed-consumables', type='http', auth='user', methods=['GET'], csrf=False)
    def get_dispensed_consumables(self, visit_id, **kw):
        """كل ما تم صرفه فعلياً لهذه الزيارة عبر dispatch-consumables — يُطابق
        على origin بالتساوي التام (وليس ilike) حتى لا تختلط زيارة رقم 1 مع 12،
        120 ...الخ. تُستخدم لإعادة عرض الأصناف المصروفة سابقاً عند إعادة فتح
        سجل المريض (PatientDispenseSection)."""
        orders = request.env['sale.order'].sudo().search([
            ('origin', '=', f'Nurse Dispatch / Visit {visit_id}'),
        ])
        items = []
        for so in orders:
            for line in so.order_line:
                items.append({
                    'sale_order_id':      so.id,
                    'sale_order_name':    so.name,
                    'product_product_id': line.product_id.id,
                    'name':               line.name or line.product_id.name,
                    'uom':                line.product_uom.name if line.product_uom else '',
                    'uom_id':             line.product_uom.id if line.product_uom else None,
                    'qty':                line.product_uom_qty,
                    'date':               str(so.create_date),
                })

        # Inpatient: dispatches land as lines on the admission's single running
        # Open Bill rather than a one-off order — only lines with an actual
        # linked stock.move are consumable dispatches (lab/rad/service lines
        # on the same bill never get one), so filter to those.
        admission = request.env['saycare.admission.request'].sudo().search(
            [('visit_id', '=', visit_id)], limit=1
        )
        if admission and admission.sale_order_id:
            so = admission.sale_order_id
            for line in so.order_line.filtered(lambda l: l.move_ids):
                items.append({
                    'sale_order_id':      so.id,
                    'sale_order_name':    so.name,
                    'product_product_id': line.product_id.id,
                    'name':               line.name or line.product_id.name,
                    'uom':                line.product_uom.name if line.product_uom else '',
                    'uom_id':             line.product_uom.id if line.product_uom else None,
                    'qty':                line.product_uom_qty,
                    'date':               str(line.create_date),
                })

        return _json(items)
