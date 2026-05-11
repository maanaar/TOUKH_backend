# -*- coding: utf-8 -*-
import json
from datetime import date, timedelta
from odoo import http, fields as odoo_fields
from odoo.http import request, Response


def http_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False, default=str)
    return Response(body, status=status, mimetype='application/json')


# ─────────────────────────────────────────────────────────────────────────────
#  product.category
# ─────────────────────────────────────────────────────────────────────────────

class CategoryController(http.Controller):

    @http.route('/api/v1/categories', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['product.category'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':                        rec.id,
                'name':                      rec.name,
                'complete_name':             rec.complete_name,
                'parent_id':                 rec.parent_id.id if rec.parent_id else None,
                'parent_name':               rec.parent_id.name if rec.parent_id else None,
                'child_ids':                 rec.child_id.ids,
                'product_count':             rec.product_count,
                # costing
                'property_cost_method':      rec.property_cost_method,
                'property_valuation':        rec.property_valuation,
                # accounts
                'property_account_income_categ_id':    rec.property_account_income_categ_id.id if rec.property_account_income_categ_id else None,
                'property_account_expense_categ_id':   rec.property_account_expense_categ_id.id if rec.property_account_expense_categ_id else None,
                'property_stock_account_input_categ_id':  rec.property_stock_account_input_categ_id.id if rec.property_stock_account_input_categ_id else None,
                'property_stock_account_output_categ_id': rec.property_stock_account_output_categ_id.id if rec.property_stock_account_output_categ_id else None,
                'property_stock_valuation_account_id':    rec.property_stock_valuation_account_id.id if rec.property_stock_valuation_account_id else None,
                'property_stock_journal':                 rec.property_stock_journal.id if rec.property_stock_journal else None,
            })
        return http_response(data)

    @http.route('/api/v1/categories/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['product.category'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        data = {
            'id':                        rec.id,
            'name':                      rec.name,
            'complete_name':             rec.complete_name,
            'parent_id':                 rec.parent_id.id if rec.parent_id else None,
            'parent_name':               rec.parent_id.name if rec.parent_id else None,
            'child_ids':                 rec.child_id.ids,
            'product_count':             rec.product_count,
            'property_cost_method':      rec.property_cost_method,
            'property_valuation':        rec.property_valuation,
            'property_account_income_categ_id':    rec.property_account_income_categ_id.id if rec.property_account_income_categ_id else None,
            'property_account_expense_categ_id':   rec.property_account_expense_categ_id.id if rec.property_account_expense_categ_id else None,
            'property_stock_account_input_categ_id':  rec.property_stock_account_input_categ_id.id if rec.property_stock_account_input_categ_id else None,
            'property_stock_account_output_categ_id': rec.property_stock_account_output_categ_id.id if rec.property_stock_account_output_categ_id else None,
            'property_stock_valuation_account_id':    rec.property_stock_valuation_account_id.id if rec.property_stock_valuation_account_id else None,
            'property_stock_journal':                 rec.property_stock_journal.id if rec.property_stock_journal else None,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  uom.uom
# ─────────────────────────────────────────────────────────────────────────────

class UomController(http.Controller):

    @http.route('/api/v1/uom', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['uom.uom'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':            rec.id,
                'name':          rec.name,
                'category_id':   rec.category_id.id if rec.category_id else None,
                'category_name': rec.category_id.name if rec.category_id else None,
                'factor':        rec.factor,
                'factor_inv':    rec.factor_inv,
                'rounding':      rec.rounding,
                'active':        rec.active,
                'uom_type':      rec.uom_type,   # bigger / reference / smaller
            })
        return http_response(data)

    @http.route('/api/v1/uom/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['uom.uom'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        data = {
            'id':            rec.id,
            'name':          rec.name,
            'category_id':   rec.category_id.id if rec.category_id else None,
            'category_name': rec.category_id.name if rec.category_id else None,
            'factor':        rec.factor,
            'factor_inv':    rec.factor_inv,
            'rounding':      rec.rounding,
            'active':        rec.active,
            'uom_type':      rec.uom_type,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  product.template
# ─────────────────────────────────────────────────────────────────────────────

class ProductController(http.Controller):

    @http.route('/api/v1/products', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['product.template'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                # ── identity ──────────────────────────────────────────────
                'id':                       rec.id,
                'name':                     rec.name,
                'default_code':             rec.default_code or '',
                'barcode':                  rec.barcode or '',
                'description':              rec.description or '',
                'description_sale':         rec.description_sale or '',
                'description_purchase':     rec.description_purchase or '',
                'description_picking':      rec.description_picking or '',
                'description_pickingout':   rec.description_pickingout or '',
                'description_pickingin':    rec.description_pickingin or '',
                # ── classification ────────────────────────────────────────
                'type':                     rec.type,           # consu / service / product
                'categ_id':                 rec.categ_id.id if rec.categ_id else None,
                'categ_name':               rec.categ_id.complete_name if rec.categ_id else None,
                'active':                   rec.active,
                'sale_ok':                  rec.sale_ok,
                'purchase_ok':              rec.purchase_ok,
                'can_be_expensed':          rec.can_be_expensed,
                # ── uom ───────────────────────────────────────────────────
                'uom_id':                   rec.uom_id.id if rec.uom_id else None,
                'uom_name':                 rec.uom_id.name if rec.uom_id else None,
                # 'uom_po_id':                rec.uom_po_id.id if rec.uom_po_id else None,
                # 'uom_po_name':              rec.uom_po_id.name if rec.uom_po_id else None,
                # ── pricing ───────────────────────────────────────────────
                'list_price':               rec.list_price,
                'standard_price':           rec.standard_price,
                'currency_id':              rec.currency_id.id if rec.currency_id else None,
                'currency_name':            rec.currency_id.name if rec.currency_id else None,
                'cost_currency_id':         rec.cost_currency_id.id if rec.cost_currency_id else None,
                # ── stock ─────────────────────────────────────────────────
                'qty_available':            rec.qty_available,
                'virtual_available':        rec.virtual_available,
                'outgoing_qty':             rec.outgoing_qty,
                'incoming_qty':             rec.incoming_qty,
                'tracking':                 rec.tracking,       # none / lot / serial
                'sale_delay':               rec.sale_delay,
                # 'produce_delay':            rec.produce_delay,
                'route_ids':                rec.route_ids.ids,
                # ── supplier ─────────────────────────────────────────────
                'seller_ids': [{
                    'partner_id':   s.partner_id.id,
                    'partner_name': s.partner_id.name,
                    'price':        s.price,
                    'min_qty':      s.min_qty,
                    'delay':        s.delay,
                    'currency_id':  s.currency_id.id if s.currency_id else None,
                } for s in rec.seller_ids],
                # ── taxes ─────────────────────────────────────────────────
                'taxes_id':                 rec.taxes_id.ids,
                'supplier_taxes_id':        rec.supplier_taxes_id.ids,
                # ── company ───────────────────────────────────────────────
                'company_id':               rec.company_id.id if rec.company_id else None,
                'company_name':             rec.company_id.name if rec.company_id else None,
                # ── responsible ───────────────────────────────────────────
                'responsible_id':           rec.responsible_id.id if rec.responsible_id else None,
                'responsible_name':         rec.responsible_id.name if rec.responsible_id else None,
                # ── image ─────────────────────────────────────────────────
                'image_url':                '/web/image/product.template/%d/image_1920' % rec.id if rec.image_1920 else '',
                # ── product variants ──────────────────────────────────────
                'product_variant_ids':      rec.product_variant_ids.ids,
                'product_variant_count':    rec.product_variant_count,
            })
        return http_response(data)

    @http.route('/api/v1/products/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['product.template'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        data = {
            'id':                       rec.id,
            'name':                     rec.name,
            'default_code':             rec.default_code or '',
            'barcode':                  rec.barcode or '',
            'description':              rec.description or '',
            'description_sale':         rec.description_sale or '',
            'description_purchase':     rec.description_purchase or '',
            'description_picking':      rec.description_picking or '',
            'description_pickingout':   rec.description_pickingout or '',
            'description_pickingin':    rec.description_pickingin or '',
            'type':                     rec.type,
            'categ_id':                 rec.categ_id.id if rec.categ_id else None,
            'categ_name':               rec.categ_id.complete_name if rec.categ_id else None,
            'active':                   rec.active,
            'sale_ok':                  rec.sale_ok,
            'purchase_ok':              rec.purchase_ok,
            'can_be_expensed':          rec.can_be_expensed,
            'uom_id':                   rec.uom_id.id if rec.uom_id else None,
            'uom_name':                 rec.uom_id.name if rec.uom_id else None,
            # 'uom_po_id':                rec.uom_po_id.id if rec.uom_po_id else None,
            # 'uom_po_name':              rec.uom_po_id.name if rec.uom_po_id else None,
            'list_price':               rec.list_price,
            'standard_price':           rec.standard_price,
            'currency_id':              rec.currency_id.id if rec.currency_id else None,
            'currency_name':            rec.currency_id.name if rec.currency_id else None,
            'cost_currency_id':         rec.cost_currency_id.id if rec.cost_currency_id else None,
            'qty_available':            rec.qty_available,
            'virtual_available':        rec.virtual_available,
            'outgoing_qty':             rec.outgoing_qty,
            'incoming_qty':             rec.incoming_qty,
            'tracking':                 rec.tracking,
            'sale_delay':               rec.sale_delay,
            # 'produce_delay':            rec.produce_delay,
            'route_ids':                rec.route_ids.ids,
            'seller_ids': [{
                'partner_id':   s.partner_id.id,
                'partner_name': s.partner_id.name,
                'price':        s.price,
                'min_qty':      s.min_qty,
                'delay':        s.delay,
                'currency_id':  s.currency_id.id if s.currency_id else None,
            } for s in rec.seller_ids],
            'taxes_id':                 rec.taxes_id.ids,
            'supplier_taxes_id':        rec.supplier_taxes_id.ids,
            'company_id':               rec.company_id.id if rec.company_id else None,
            'company_name':             rec.company_id.name if rec.company_id else None,
            'responsible_id':           rec.responsible_id.id if rec.responsible_id else None,
            'responsible_name':         rec.responsible_id.name if rec.responsible_id else None,
            'image_url':                '/web/image/product.template/%d/image_1920' % rec.id if rec.image_1920 else '',
            'product_variant_ids':      rec.product_variant_ids.ids,
            'product_variant_count':    rec.product_variant_count,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.location
# ─────────────────────────────────────────────────────────────────────────────

class LocationController(http.Controller):

    @http.route('/api/v1/stock/locations', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.location'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':                   rec.id,
                'name':                 rec.name,
                'complete_name':        rec.complete_name,
                'usage':                rec.usage,      # supplier/view/internal/customer/inventory/production/transit
                'location_id':          rec.location_id.id if rec.location_id else None,
                'parent_name':          rec.location_id.complete_name if rec.location_id else None,
                'child_ids':            rec.child_ids.ids,
                'active':               rec.active,
                'scrap_location':       rec.scrap_location,
                'return_location':      rec.return_location,
                'replenish_location':   rec.replenish_location,
                'comment':              rec.comment or '',
                'posx':                 rec.posx,
                'posy':                 rec.posy,
                'posz':                 rec.posz,
                'barcode':              rec.barcode or '',
                'removal_strategy_id':  rec.removal_strategy_id.id if rec.removal_strategy_id else None,
                'removal_strategy_name': rec.removal_strategy_id.name if rec.removal_strategy_id else None,
                'cyclic_inventory_frequency': rec.cyclic_inventory_frequency,
                'last_inventory_date':  str(rec.last_inventory_date) if rec.last_inventory_date else None,
                'next_inventory_date':  str(rec.next_inventory_date) if rec.next_inventory_date else None,
                'company_id':           rec.company_id.id if rec.company_id else None,
                'company_name':         rec.company_id.name if rec.company_id else None,
                'warehouse_id':         rec.warehouse_id.id if rec.warehouse_id else None,
                'warehouse_name':       rec.warehouse_id.name if rec.warehouse_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/stock/locations/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['stock.location'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        data = {
            'id':                   rec.id,
            'name':                 rec.name,
            'complete_name':        rec.complete_name,
            'usage':                rec.usage,
            'location_id':          rec.location_id.id if rec.location_id else None,
            'parent_name':          rec.location_id.complete_name if rec.location_id else None,
            'child_ids':            rec.child_ids.ids,
            'active':               rec.active,
            'scrap_location':       rec.scrap_location,
            'return_location':      rec.return_location,
            'replenish_location':   rec.replenish_location,
            'comment':              rec.comment or '',
            'posx':                 rec.posx,
            'posy':                 rec.posy,
            'posz':                 rec.posz,
            'barcode':              rec.barcode or '',
            'removal_strategy_id':  rec.removal_strategy_id.id if rec.removal_strategy_id else None,
            'removal_strategy_name': rec.removal_strategy_id.name if rec.removal_strategy_id else None,
            'cyclic_inventory_frequency': rec.cyclic_inventory_frequency,
            'last_inventory_date':  str(rec.last_inventory_date) if rec.last_inventory_date else None,
            'next_inventory_date':  str(rec.next_inventory_date) if rec.next_inventory_date else None,
            'company_id':           rec.company_id.id if rec.company_id else None,
            'company_name':         rec.company_id.name if rec.company_id else None,
            'warehouse_id':         rec.warehouse_id.id if rec.warehouse_id else None,
            'warehouse_name':       rec.warehouse_id.name if rec.warehouse_id else None,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.picking  +  stock.move (جوا الـ picking)
# ─────────────────────────────────────────────────────────────────────────────

class PickingController(http.Controller):

    @http.route('/api/v1/stock/pickings', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.picking'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                # ── identity ──────────────────────────────────────────────
                'id':                       rec.id,
                'name':                     rec.name,
                'origin':                   rec.origin or '',
                'note':                     rec.note or '',
                'state':                    rec.state,
                'priority':                 rec.priority,       # 0=Normal 1=Urgent
                'move_type':                rec.move_type,      # direct / one
                # ── type / operation ──────────────────────────────────────
                'picking_type_id':          rec.picking_type_id.id if rec.picking_type_id else None,
                'picking_type_name':        rec.picking_type_id.name if rec.picking_type_id else None,
                'picking_type_code':        rec.picking_type_id.code if rec.picking_type_id else None,  # incoming/outgoing/internal
                # ── partner ───────────────────────────────────────────────
                'partner_id':               rec.partner_id.id if rec.partner_id else None,
                'partner_name':             rec.partner_id.name if rec.partner_id else None,
                # ── locations ─────────────────────────────────────────────
                'location_id':              rec.location_id.id if rec.location_id else None,
                'location_name':            rec.location_id.complete_name if rec.location_id else None,
                'location_dest_id':         rec.location_dest_id.id if rec.location_dest_id else None,
                'location_dest_name':       rec.location_dest_id.complete_name if rec.location_dest_id else None,
                # ── dates ─────────────────────────────────────────────────
                'scheduled_date':           str(rec.scheduled_date) if rec.scheduled_date else None,
                'date_deadline':            str(rec.date_deadline) if rec.date_deadline else None,
                'date_done':                str(rec.date_done) if rec.date_done else None,
                # ── counts ────────────────────────────────────────────────
                'product_id':               rec.product_id.id if rec.product_id else None,  # computed if single product
                'move_ids_count':           len(rec.move_ids),
                # ── links ─────────────────────────────────────────────────
                'purchase_id':              rec.purchase_id.id if rec.purchase_id else None,
                'purchase_name':            rec.purchase_id.name if rec.purchase_id else None,
                'sale_id':                  rec.sale_id.id if rec.sale_id else None,
                'sale_name':                rec.sale_id.name if rec.sale_id else None,
                'backorder_id':             rec.backorder_id.id if rec.backorder_id else None,
                'backorder_name':           rec.backorder_id.name if rec.backorder_id else None,
                # ── responsible ───────────────────────────────────────────
                'user_id':                  rec.user_id.id if rec.user_id else None,
                'user_name':                rec.user_id.name if rec.user_id else None,
                'owner_id':                 rec.owner_id.id if rec.owner_id else None,
                'owner_name':               rec.owner_id.name if rec.owner_id else None,
                # ── company ───────────────────────────────────────────────
                'company_id':               rec.company_id.id if rec.company_id else None,
                'company_name':             rec.company_id.name if rec.company_id else None,
                # ── bool flags ────────────────────────────────────────────
                'is_locked':                rec.is_locked,
                'immediate_transfer':       rec.immediate_transfer,
            })
        return http_response(data)

    @http.route('/api/v1/stock/pickings/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['stock.picking'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)

        moves = []
        for move in rec.move_ids:
            moves.append({
                'id':                       move.id,
                'name':                     move.name,
                'reference':                move.reference or '',
                'origin':                   move.origin or '',
                'state':                    move.state,
                'priority':                 move.priority,
                # ── product ───────────────────────────────────────────────
                'product_id':               move.product_id.id if move.product_id else None,
                'product_name':             move.product_id.name if move.product_id else None,
                'product_default_code':     move.product_id.default_code or '' if move.product_id else '',
                'description_picking':      move.description_picking or '',
                # ── qty ───────────────────────────────────────────────────
                'product_uom_qty':          move.product_uom_qty,   # demand
                'quantity':                 move.quantity,           # done
                'reserved_availability':    move.reserved_availability,
                'availability':             move.availability,
                # ── uom ───────────────────────────────────────────────────
                'product_uom':              move.product_uom.id if move.product_uom else None,
                'product_uom_name':         move.product_uom.name if move.product_uom else None,
                # ── locations ─────────────────────────────────────────────
                'location_id':              move.location_id.id if move.location_id else None,
                'location_name':            move.location_id.complete_name if move.location_id else None,
                'location_dest_id':         move.location_dest_id.id if move.location_dest_id else None,
                'location_dest_name':       move.location_dest_id.complete_name if move.location_dest_id else None,
                # ── lot / serial ──────────────────────────────────────────
                'lot_ids':                  move.lot_ids.ids,
                'lot_names':                move.lot_ids.mapped('name'),
                # ── dates ─────────────────────────────────────────────────
                'date':                     str(move.date) if move.date else None,
                'date_deadline':            str(move.date_deadline) if move.date_deadline else None,
                # ── financials ────────────────────────────────────────────
                'price_unit':               move.price_unit,
                'value':                    move.value,
                # ── links ─────────────────────────────────────────────────
                'purchase_line_id':         move.purchase_line_id.id if move.purchase_line_id else None,
                'sale_line_id':             move.sale_line_id.id if move.sale_line_id else None,
                'move_orig_ids':            move.move_orig_ids.ids,
                'move_dest_ids':            move.move_dest_ids.ids,
                # ── company ───────────────────────────────────────────────
                'company_id':               move.company_id.id if move.company_id else None,
                'company_name':             move.company_id.name if move.company_id else None,
                # ── picking ───────────────────────────────────────────────
                'picking_id':               move.picking_id.id if move.picking_id else None,
                'picking_name':             move.picking_id.name if move.picking_id else None,
                # ── move_line_ids (detailed) ──────────────────────────────
                'move_line_ids': [{
                    'id':               ml.id,
                    'lot_id':           ml.lot_id.id if ml.lot_id else None,
                    'lot_name':         ml.lot_id.name if ml.lot_id else None,
                    'quantity':         ml.quantity,
                    'qty_done':         ml.qty_done,
                    'location_id':      ml.location_id.id if ml.location_id else None,
                    'location_dest_id': ml.location_dest_id.id if ml.location_dest_id else None,
                    'package_id':       ml.package_id.id if ml.package_id else None,
                    'result_package_id': ml.result_package_id.id if ml.result_package_id else None,
                } for ml in move.move_line_ids],
            })

        data = {
            'id':                       rec.id,
            'name':                     rec.name,
            'origin':                   rec.origin or '',
            'note':                     rec.note or '',
            'state':                    rec.state,
            'priority':                 rec.priority,
            'move_type':                rec.move_type,
            'picking_type_id':          rec.picking_type_id.id if rec.picking_type_id else None,
            'picking_type_name':        rec.picking_type_id.name if rec.picking_type_id else None,
            'picking_type_code':        rec.picking_type_id.code if rec.picking_type_id else None,
            'partner_id':               rec.partner_id.id if rec.partner_id else None,
            'partner_name':             rec.partner_id.name if rec.partner_id else None,
            'location_id':              rec.location_id.id if rec.location_id else None,
            'location_name':            rec.location_id.complete_name if rec.location_id else None,
            'location_dest_id':         rec.location_dest_id.id if rec.location_dest_id else None,
            'location_dest_name':       rec.location_dest_id.complete_name if rec.location_dest_id else None,
            'scheduled_date':           str(rec.scheduled_date) if rec.scheduled_date else None,
            'date_deadline':            str(rec.date_deadline) if rec.date_deadline else None,
            'date_done':                str(rec.date_done) if rec.date_done else None,
            'purchase_id':              rec.purchase_id.id if rec.purchase_id else None,
            'purchase_name':            rec.purchase_id.name if rec.purchase_id else None,
            'sale_id':                  rec.sale_id.id if rec.sale_id else None,
            'sale_name':                rec.sale_id.name if rec.sale_id else None,
            'backorder_id':             rec.backorder_id.id if rec.backorder_id else None,
            'backorder_name':           rec.backorder_id.name if rec.backorder_id else None,
            'user_id':                  rec.user_id.id if rec.user_id else None,
            'user_name':                rec.user_id.name if rec.user_id else None,
            'owner_id':                 rec.owner_id.id if rec.owner_id else None,
            'owner_name':               rec.owner_id.name if rec.owner_id else None,
            'company_id':               rec.company_id.id if rec.company_id else None,
            'company_name':             rec.company_id.name if rec.company_id else None,
            'is_locked':                rec.is_locked,
            'immediate_transfer':       rec.immediate_transfer,
            'moves':                    moves,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.move  (endpoint مستقل)
# ─────────────────────────────────────────────────────────────────────────────

class MoveController(http.Controller):

    @http.route('/api/v1/stock/moves', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.move'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':                       rec.id,
                'name':                     rec.name,
                'reference':                rec.reference or '',
                'origin':                   rec.origin or '',
                'state':                    rec.state,
                'priority':                 rec.priority,
                # ── product ───────────────────────────────────────────────
                'product_id':               rec.product_id.id if rec.product_id else None,
                'product_name':             rec.product_id.name if rec.product_id else None,
                'product_default_code':     rec.product_id.default_code or '' if rec.product_id else '',
                'description_picking':      rec.description_picking or '',
                # ── qty ───────────────────────────────────────────────────
                'product_uom_qty':          rec.product_uom_qty,
                'quantity':                 rec.quantity,
                'reserved_availability':    rec.reserved_availability,
                'availability':             rec.availability,
                # ── uom ───────────────────────────────────────────────────
                'product_uom':              rec.product_uom.id if rec.product_uom else None,
                'product_uom_name':         rec.product_uom.name if rec.product_uom else None,
                # ── locations ─────────────────────────────────────────────
                'location_id':              rec.location_id.id if rec.location_id else None,
                'location_name':            rec.location_id.complete_name if rec.location_id else None,
                'location_dest_id':         rec.location_dest_id.id if rec.location_dest_id else None,
                'location_dest_name':       rec.location_dest_id.complete_name if rec.location_dest_id else None,
                # ── lot / serial ──────────────────────────────────────────
                'lot_ids':                  rec.lot_ids.ids,
                'lot_names':                rec.lot_ids.mapped('name'),
                # ── dates ─────────────────────────────────────────────────
                'date':                     str(rec.date) if rec.date else None,
                'date_deadline':            str(rec.date_deadline) if rec.date_deadline else None,
                # ── financials ────────────────────────────────────────────
                'price_unit':               rec.price_unit,
                'value':                    rec.value,
                # ── links ─────────────────────────────────────────────────
                'picking_id':               rec.picking_id.id if rec.picking_id else None,
                'picking_name':             rec.picking_id.name if rec.picking_id else None,
                'purchase_line_id':         rec.purchase_line_id.id if rec.purchase_line_id else None,
                'sale_line_id':             rec.sale_line_id.id if rec.sale_line_id else None,
                'move_orig_ids':            rec.move_orig_ids.ids,
                'move_dest_ids':            rec.move_dest_ids.ids,
                # ── company ───────────────────────────────────────────────
                'company_id':               rec.company_id.id if rec.company_id else None,
                'company_name':             rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  purchase.order
# ─────────────────────────────────────────────────────────────────────────────

class PurchaseOrderController(http.Controller):

    @http.route('/api/v1/purchase/orders', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['purchase.order'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                # ── identity ──────────────────────────────────────────────
                'id':                   rec.id,
                'name':                 rec.name,
                'state':                rec.state,      # draft/sent/purchase/done/cancel
                'priority':             rec.priority,
                'origin':               rec.origin or '',
                'partner_ref':          rec.partner_ref or '',
                'note':                 rec.notes or '',
                # ── partner ───────────────────────────────────────────────
                'partner_id':           rec.partner_id.id if rec.partner_id else None,
                'partner_name':         rec.partner_id.name if rec.partner_id else None,
                'dest_address_id':      rec.dest_address_id.id if rec.dest_address_id else None,
                'dest_address_name':    rec.dest_address_id.name if rec.dest_address_id else None,
                # ── dates ─────────────────────────────────────────────────
                'date_order':           str(rec.date_order) if rec.date_order else None,
                'date_approve':         str(rec.date_approve) if rec.date_approve else None,
                'date_planned':         str(rec.date_planned) if rec.date_planned else None,
                'date_calendar_start':  str(rec.date_calendar_start) if rec.date_calendar_start else None,
                # ── financials ────────────────────────────────────────────
                'currency_id':          rec.currency_id.id if rec.currency_id else None,
                'currency_name':        rec.currency_id.name if rec.currency_id else None,
                'amount_untaxed':       rec.amount_untaxed,
                'amount_tax':           rec.amount_tax,
                'amount_total':         rec.amount_total,
                'tax_totals':           rec.tax_totals,
                # ── payment terms ─────────────────────────────────────────
                'payment_term_id':      rec.payment_term_id.id if rec.payment_term_id else None,
                'payment_term_name':    rec.payment_term_id.name if rec.payment_term_id else None,
                # ── incoterms ─────────────────────────────────────────────
                'incoterm_id':          rec.incoterm_id.id if rec.incoterm_id else None,
                'incoterm_name':        rec.incoterm_id.name if rec.incoterm_id else None,
                # ── fiscal position ───────────────────────────────────────
                'fiscal_position_id':   rec.fiscal_position_id.id if rec.fiscal_position_id else None,
                'fiscal_position_name': rec.fiscal_position_id.name if rec.fiscal_position_id else None,
                # ── status ────────────────────────────────────────────────
                'invoice_status':       rec.invoice_status,     # nothing/to invoice/invoiced
                'billing_count':        rec.invoice_count,
                'incoming_picking_count': rec.incoming_picking_count,
                'picking_ids':          rec.picking_ids.ids,
                'invoice_ids':          rec.invoice_ids.ids,
                # ── responsible ───────────────────────────────────────────
                'user_id':              rec.user_id.id if rec.user_id else None,
                'user_name':            rec.user_id.name if rec.user_id else None,
                # ── company / warehouse ───────────────────────────────────
                'company_id':           rec.company_id.id if rec.company_id else None,
                'company_name':         rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/purchase/orders/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['purchase.order'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)

        lines = []
        for line in rec.order_line:
            lines.append({
                'id':                       line.id,
                'sequence':                 line.sequence,
                'display_type':             line.display_type or '',    # line_section / line_note / False
                # ── product ───────────────────────────────────────────────
                'product_id':               line.product_id.id if line.product_id else None,
                'product_name':             line.product_id.name if line.product_id else None,
                'product_default_code':     line.product_id.default_code or '' if line.product_id else '',
                'name':                     line.name or '',
                # ── qty ───────────────────────────────────────────────────
                'product_qty':              line.product_qty,
                'qty_received':             line.qty_received,
                'qty_invoiced':             line.qty_invoiced,
                'qty_to_invoice':           line.qty_to_invoice,
                # ── uom ───────────────────────────────────────────────────
                'product_uom':              line.product_uom.id if line.product_uom else None,
                'product_uom_name':         line.product_uom.name if line.product_uom else None,
                # ── pricing ───────────────────────────────────────────────
                'price_unit':               line.price_unit,
                'discount':                 line.discount,
                'taxes_id':                 line.taxes_id.ids,
                'price_subtotal':           line.price_subtotal,
                'price_total':              line.price_total,
                'price_tax':                line.price_tax,
                # ── dates ─────────────────────────────────────────────────
                'date_planned':             str(line.date_planned) if line.date_planned else None,
                # ── links ─────────────────────────────────────────────────
                'account_analytic_id':      line.account_analytic_id.id if line.account_analytic_id else None,
                'analytic_distribution':    line.analytic_distribution or {},
                'move_ids':                 line.move_ids.ids,
                'invoice_lines':            line.invoice_lines.ids,
                # ── company ───────────────────────────────────────────────
                'company_id':               line.company_id.id if line.company_id else None,
            })

        data = {
            'id':                   rec.id,
            'name':                 rec.name,
            'state':                rec.state,
            'priority':             rec.priority,
            'origin':               rec.origin or '',
            'partner_ref':          rec.partner_ref or '',
            'note':                 rec.notes or '',
            'partner_id':           rec.partner_id.id if rec.partner_id else None,
            'partner_name':         rec.partner_id.name if rec.partner_id else None,
            'dest_address_id':      rec.dest_address_id.id if rec.dest_address_id else None,
            'dest_address_name':    rec.dest_address_id.name if rec.dest_address_id else None,
            'date_order':           str(rec.date_order) if rec.date_order else None,
            'date_approve':         str(rec.date_approve) if rec.date_approve else None,
            'date_planned':         str(rec.date_planned) if rec.date_planned else None,
            'currency_id':          rec.currency_id.id if rec.currency_id else None,
            'currency_name':        rec.currency_id.name if rec.currency_id else None,
            'amount_untaxed':       rec.amount_untaxed,
            'amount_tax':           rec.amount_tax,
            'amount_total':         rec.amount_total,
            'payment_term_id':      rec.payment_term_id.id if rec.payment_term_id else None,
            'payment_term_name':    rec.payment_term_id.name if rec.payment_term_id else None,
            'incoterm_id':          rec.incoterm_id.id if rec.incoterm_id else None,
            'incoterm_name':        rec.incoterm_id.name if rec.incoterm_id else None,
            'fiscal_position_id':   rec.fiscal_position_id.id if rec.fiscal_position_id else None,
            'fiscal_position_name': rec.fiscal_position_id.name if rec.fiscal_position_id else None,
            'invoice_status':       rec.invoice_status,
            'picking_ids':          rec.picking_ids.ids,
            'invoice_ids':          rec.invoice_ids.ids,
            'user_id':              rec.user_id.id if rec.user_id else None,
            'user_name':            rec.user_id.name if rec.user_id else None,
            'company_id':           rec.company_id.id if rec.company_id else None,
            'company_name':         rec.company_id.name if rec.company_id else None,
            'order_lines':          lines,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  employee.purchase.requisition
#  model: employee.purchase.requisition  |  lines: requisition.order
# ─────────────────────────────────────────────────────────────────────────────

class RequisitionController(http.Controller):

    @http.route('/api/v1/purchase/requisitions', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['employee.purchase.requisition'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                # ── identity ──────────────────────────────────────────────
                'id':                           rec.id,
                'name':                         rec.name,
                'state':                        rec.state,
                # state values: new / waiting_department_approval / waiting_head_approval
                #               approved / purchase_order_created / received / cancelled
                'requisition_description':      rec.requisition_description or '',
                # ── employee / responsible people ─────────────────────────
                'employee_id':                  rec.employee_id.id if rec.employee_id else None,
                'employee_name':                rec.employee_id.name if rec.employee_id else None,
                'dept_id':                      rec.dept_id.id if rec.dept_id else None,
                'dept_name':                    rec.dept_id.name if rec.dept_id else None,
                'user_id':                      rec.user_id.id if rec.user_id else None,
                'user_name':                    rec.user_id.name if rec.user_id else None,
                'confirm_id':                   rec.confirm_id.id if rec.confirm_id else None,
                'confirm_name':                 rec.confirm_id.name if rec.confirm_id else None,
                'manager_id':                   rec.manager_id.id if rec.manager_id else None,
                'manager_name':                 rec.manager_id.name if rec.manager_id else None,
                'requisition_head_id':          rec.requisition_head_id.id if rec.requisition_head_id else None,
                'requisition_head_name':        rec.requisition_head_id.name if rec.requisition_head_id else None,
                'rejected_user_id':             rec.rejected_user_id.id if rec.rejected_user_id else None,
                'rejected_user_name':           rec.rejected_user_id.name if rec.rejected_user_id else None,
                # ── dates ─────────────────────────────────────────────────
                'requisition_date':             str(rec.requisition_date) if rec.requisition_date else None,
                'requisition_deadline':         str(rec.requisition_deadline) if rec.requisition_deadline else None,
                'receive_date':                 str(rec.receive_date) if rec.receive_date else None,
                'confirmed_date':               str(rec.confirmed_date) if rec.confirmed_date else None,
                'department_approval_date':     str(rec.department_approval_date) if rec.department_approval_date else None,
                'approval_date':                str(rec.approval_date) if rec.approval_date else None,
                'reject_date':                  str(rec.reject_date) if rec.reject_date else None,
                # ── stock / delivery ──────────────────────────────────────
                'source_location_id':           rec.source_location_id.id if rec.source_location_id else None,
                'source_location_name':         rec.source_location_id.complete_name if rec.source_location_id else None,
                'destination_location_id':      rec.destination_location_id.id if rec.destination_location_id else None,
                'destination_location_name':    rec.destination_location_id.complete_name if rec.destination_location_id else None,
                'delivery_type_id':             rec.delivery_type_id.id if rec.delivery_type_id else None,
                'delivery_type_name':           rec.delivery_type_id.name if rec.delivery_type_id else None,
                'internal_picking_id':          rec.internal_picking_id.id if rec.internal_picking_id else None,
                'internal_picking_name':        rec.internal_picking_id.name if rec.internal_picking_id else None,
                # ── counts ────────────────────────────────────────────────
                'purchase_count':               rec.purchase_count,
                'internal_transfer_count':      rec.internal_transfer_count,
                # ── company ───────────────────────────────────────────────
                'company_id':                   rec.company_id.id if rec.company_id else None,
                'company_name':                 rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/purchase/requisitions/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['employee.purchase.requisition'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)

        # one2many: requisition_order_ids  →  model: requisition.order
        lines = []
        for line in rec.requisition_order_ids:
            lines.append({
                'id':               line.id,
                'product_id':       line.product_id.id if line.product_id else None,
                'product_name':     line.product_id.name if line.product_id else None,
                'default_code':     line.product_id.default_code or '' if line.product_id else '',
                'quantity':         line.quantity,
                'requisition_type': line.requisition_type,   # purchase_order / internal_transfer
                'partner_id':       line.partner_id.id if line.partner_id else None,
                'partner_name':     line.partner_id.name if line.partner_id else None,
            })

        data = {
            'id':                           rec.id,
            'name':                         rec.name,
            'state':                        rec.state,
            'requisition_description':      rec.requisition_description or '',
            'employee_id':                  rec.employee_id.id if rec.employee_id else None,
            'employee_name':                rec.employee_id.name if rec.employee_id else None,
            'dept_id':                      rec.dept_id.id if rec.dept_id else None,
            'dept_name':                    rec.dept_id.name if rec.dept_id else None,
            'user_id':                      rec.user_id.id if rec.user_id else None,
            'user_name':                    rec.user_id.name if rec.user_id else None,
            'confirm_id':                   rec.confirm_id.id if rec.confirm_id else None,
            'confirm_name':                 rec.confirm_id.name if rec.confirm_id else None,
            'manager_id':                   rec.manager_id.id if rec.manager_id else None,
            'manager_name':                 rec.manager_id.name if rec.manager_id else None,
            'requisition_head_id':          rec.requisition_head_id.id if rec.requisition_head_id else None,
            'requisition_head_name':        rec.requisition_head_id.name if rec.requisition_head_id else None,
            'rejected_user_id':             rec.rejected_user_id.id if rec.rejected_user_id else None,
            'rejected_user_name':           rec.rejected_user_id.name if rec.rejected_user_id else None,
            'requisition_date':             str(rec.requisition_date) if rec.requisition_date else None,
            'requisition_deadline':         str(rec.requisition_deadline) if rec.requisition_deadline else None,
            'receive_date':                 str(rec.receive_date) if rec.receive_date else None,
            'confirmed_date':               str(rec.confirmed_date) if rec.confirmed_date else None,
            'department_approval_date':     str(rec.department_approval_date) if rec.department_approval_date else None,
            'approval_date':                str(rec.approval_date) if rec.approval_date else None,
            'reject_date':                  str(rec.reject_date) if rec.reject_date else None,
            'source_location_id':           rec.source_location_id.id if rec.source_location_id else None,
            'source_location_name':         rec.source_location_id.complete_name if rec.source_location_id else None,
            'destination_location_id':      rec.destination_location_id.id if rec.destination_location_id else None,
            'destination_location_name':    rec.destination_location_id.complete_name if rec.destination_location_id else None,
            'delivery_type_id':             rec.delivery_type_id.id if rec.delivery_type_id else None,
            'delivery_type_name':           rec.delivery_type_id.name if rec.delivery_type_id else None,
            'internal_picking_id':          rec.internal_picking_id.id if rec.internal_picking_id else None,
            'internal_picking_name':        rec.internal_picking_id.name if rec.internal_picking_id else None,
            'purchase_count':               rec.purchase_count,
            'internal_transfer_count':      rec.internal_transfer_count,
            'company_id':                   rec.company_id.id if rec.company_id else None,
            'company_name':                 rec.company_id.name if rec.company_id else None,
            'requisition_order_ids':        lines,
        }
        return http_response(data)

# ─────────────────────────────────────────────────────────────────────────────
#  CREATE endpoints  (POST)
# ─────────────────────────────────────────────────────────────────────────────

# ── POST /api/v1/categories ──────────────────────────────────────────────────
#
#  Required body (JSON):
#    name        : string
#  Optional body:
#    parent_id   : int
#
#  Example:
#    curl -u admin:admin -X POST http://localhost:8069/api/v1/categories \
#         -H "Content-Type: application/json" \
#         -d '{"name": "Electronics", "parent_id": 1}'
# ─────────────────────────────────────────────────────────────────────────────

class CategoryCreateController(http.Controller):

    @http.route('/api/v1/categories', type='http', auth='user', methods=['POST'], csrf=False)
    def create_category(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            # ── validate required fields ──────────────────────────────────
            if not body.get('name'):
                return http_response({'error': 'name is required'}, 400)

            vals = {
                'name': body['name'],
            }

            if body.get('parent_id'):
                parent = request.env['product.category'].sudo().browse(int(body['parent_id']))
                if not parent.exists():
                    return http_response({'error': 'parent_id not found'}, 400)
                vals['parent_id'] = parent.id

            rec = request.env['product.category'].sudo().create(vals)

            return http_response({
                'id':            rec.id,
                'name':          rec.name,
                'complete_name': rec.complete_name,
                'parent_id':     rec.parent_id.id if rec.parent_id else None,
                'parent_name':   rec.parent_id.name if rec.parent_id else None,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ── POST /api/v1/products ─────────────────────────────────────────────────────
#
#  Required body (JSON):
#    name        : string
#  Optional body:
#    default_code        : string
#    barcode             : string
#    type                : 'consu' | 'service' | 'product'   (default: 'consu')
#    categ_id            : int
#    uom_id              : int
#    uom_po_id           : int
#    list_price          : float
#    standard_price      : float
#    sale_ok             : bool
#    purchase_ok         : bool
#    description         : string
#    description_sale    : string
#    description_purchase: string
#    tracking            : 'none' | 'lot' | 'serial'
#
#  Example:
#    curl -u admin:admin -X POST http://localhost:8069/api/v1/products \
#         -H "Content-Type: application/json" \
#         -d '{"name": "Laptop", "type": "product", "categ_id": 5, "list_price": 1500.0}'
# ─────────────────────────────────────────────────────────────────────────────

class ProductCreateController(http.Controller):

    @http.route('/api/v1/products', type='http', auth='user', methods=['POST'], csrf=False)
    def create_product(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            # ── validate required fields ──────────────────────────────────
            if not body.get('name'):
                return http_response({'error': 'name is required'}, 400)

            vals = {
                'name': body['name'],
            }

            # ── optional simple fields ────────────────────────────────────
            for field in ['default_code', 'barcode', 'type', 'list_price',
                          'standard_price', 'sale_ok', 'purchase_ok',
                          'description', 'description_sale',
                          'description_purchase', 'tracking',
                          'description_picking', 'description_pickingout',
                          'description_pickingin']:
                if field in body:
                    vals[field] = body[field]

            # ── many2one fields – validate existence ──────────────────────
            m2o_fields = {
                'categ_id':   'product.category',
                'uom_id':     'uom.uom',
                'uom_po_id':  'uom.uom',
            }
            for field, model in m2o_fields.items():
                if body.get(field):
                    related = request.env[model].sudo().browse(int(body[field]))
                    if not related.exists():
                        return http_response({'error': f'{field} not found'}, 400)
                    vals[field] = related.id

            rec = request.env['product.template'].sudo().create(vals)

            return http_response({
                'id':             rec.id,
                'name':           rec.name,
                'default_code':   rec.default_code or '',
                'barcode':        rec.barcode or '',
                'type':           rec.type,
                'categ_id':       rec.categ_id.id if rec.categ_id else None,
                'categ_name':     rec.categ_id.name if rec.categ_id else None,
                'uom_id':         rec.uom_id.id if rec.uom_id else None,
                'uom_name':       rec.uom_id.name if rec.uom_id else None,
                # 'uom_po_id':      rec.uom_po_id.id if rec.uom_po_id else None,
                # 'uom_po_name':    rec.uom_po_id.name if rec.uom_po_id else None,
                'list_price':     rec.list_price,
                'standard_price': rec.standard_price,
                'sale_ok':        rec.sale_ok,
                'purchase_ok':    rec.purchase_ok,
                'tracking':       rec.tracking,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ── POST /api/v1/purchase/requisitions ───────────────────────────────────────
#
#  Required body (JSON):
#    employee_id  : int
#    user_id      : int   (responsible)
#    lines        : list of objects:
#        product_id        : int      (required)
#        quantity          : float    (required)
#        requisition_type  : 'purchase_order' | 'internal_transfer'   (required)
#        partner_id        : int      (required if requisition_type = 'purchase_order')
#
#  Optional body:
#    requisition_date     : 'YYYY-MM-DD'
#    requisition_deadline : 'YYYY-MM-DD'
#    requisition_description : string
#    company_id           : int
#
#  Example:
#    curl -u admin:admin -X POST http://localhost:8069/api/v1/purchase/requisitions \
#         -H "Content-Type: application/json" \
#         -d '{
#               "employee_id": 3,
#               "user_id": 2,
#               "requisition_description": "Need office supplies",
#               "lines": [
#                   {"product_id": 10, "quantity": 5,
#                    "requisition_type": "purchase_order", "partner_id": 7},
#                   {"product_id": 14, "quantity": 2,
#                    "requisition_type": "internal_transfer"}
#               ]
#             }'
# ─────────────────────────────────────────────────────────────────────────────

class RequisitionCreateController(http.Controller):

    @http.route('/api/v1/purchase/requisitions', type='http', auth='user', methods=['POST'], csrf=False)
    def create_requisition(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            # ── validate required header fields ───────────────────────────
            if not body.get('employee_id'):
                return http_response({'error': 'employee_id is required'}, 400)
            if not body.get('user_id'):
                return http_response({'error': 'user_id is required'}, 400)
            if not body.get('lines'):
                return http_response({'error': 'lines is required and must not be empty'}, 400)

            # ── validate employee ─────────────────────────────────────────
            employee = request.env['hr.employee'].sudo().browse(int(body['employee_id']))
            if not employee.exists():
                return http_response({'error': 'employee_id not found'}, 400)

            # ── validate responsible user ─────────────────────────────────
            user = request.env['res.users'].sudo().browse(int(body['user_id']))
            if not user.exists():
                return http_response({'error': 'user_id not found'}, 400)

            # ── build header vals ─────────────────────────────────────────
            vals = {
                'employee_id': employee.id,
                'user_id':     user.id,
            }

            for field in ['requisition_date', 'requisition_deadline', 'requisition_description']:
                if body.get(field):
                    vals[field] = body[field]

            if body.get('company_id'):
                company = request.env['res.company'].sudo().browse(int(body['company_id']))
                if not company.exists():
                    return http_response({'error': 'company_id not found'}, 400)
                vals['company_id'] = company.id

            # ── validate and build lines ──────────────────────────────────
            VALID_TYPES = ('purchase_order', 'internal_transfer')
            line_vals_list = []

            for i, line in enumerate(body['lines']):
                # product
                if not line.get('product_id'):
                    return http_response({'error': f'lines[{i}]: product_id is required'}, 400)
                product = request.env['product.product'].sudo().browse(int(line['product_id']))
                if not product.exists():
                    return http_response({'error': f'lines[{i}]: product_id not found'}, 400)

                # quantity
                if not line.get('quantity'):
                    return http_response({'error': f'lines[{i}]: quantity is required'}, 400)

                # requisition_type
                req_type = line.get('requisition_type')
                if req_type not in VALID_TYPES:
                    return http_response(
                        {'error': f'lines[{i}]: requisition_type must be one of {VALID_TYPES}'}, 400
                    )

                line_val = {
                    'product_id':       product.id,
                    'quantity':         float(line['quantity']),
                    'requisition_type': req_type,
                }

                # partner required for purchase_order
                if req_type == 'purchase_order':
                    if not line.get('partner_id'):
                        return http_response(
                            {'error': f'lines[{i}]: partner_id is required when requisition_type is purchase_order'}, 400
                        )
                    partner = request.env['res.partner'].sudo().browse(int(line['partner_id']))
                    if not partner.exists():
                        return http_response({'error': f'lines[{i}]: partner_id not found'}, 400)
                    line_val['partner_id'] = partner.id

                line_vals_list.append((0, 0, line_val))

            vals['requisition_order_ids'] = line_vals_list

            # ── create ────────────────────────────────────────────────────
            rec = request.env['employee.purchase.requisition'].sudo().create(vals)

            return http_response({
                'id':                       rec.id,
                'name':                     rec.name,
                'state':                    rec.state,
                'employee_id':              rec.employee_id.id,
                'employee_name':            rec.employee_id.name,
                'dept_id':                  rec.dept_id.id if rec.dept_id else None,
                'dept_name':                rec.dept_id.name if rec.dept_id else None,
                'user_id':                  rec.user_id.id,
                'user_name':                rec.user_id.name,
                'requisition_date':         str(rec.requisition_date) if rec.requisition_date else None,
                'requisition_deadline':     str(rec.requisition_deadline) if rec.requisition_deadline else None,
                'requisition_description':  rec.requisition_description or '',
                'company_id':               rec.company_id.id if rec.company_id else None,
                'company_name':             rec.company_id.name if rec.company_id else None,
                'requisition_order_ids': [{
                    'id':               line.id,
                    'product_id':       line.product_id.id,
                    'product_name':     line.product_id.name,
                    'quantity':         line.quantity,
                    'requisition_type': line.requisition_type,
                    'partner_id':       line.partner_id.id if line.partner_id else None,
                    'partner_name':     line.partner_id.name if line.partner_id else None,
                } for line in rec.requisition_order_ids],
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  UPDATE endpoints  (PUT)
# ─────────────────────────────────────────────────────────────────────────────

class ProductUpdateController(http.Controller):

    @http.route('/api/v1/products/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_product(self, rec_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
            rec = request.env['product.template'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            vals = {}
            for field in ['name', 'default_code', 'barcode', 'type', 'list_price',
                          'standard_price', 'sale_ok', 'purchase_ok', 'active',
                          'description', 'description_sale', 'description_purchase',
                          'tracking', 'description_picking', 'description_pickingout',
                          'description_pickingin']:
                if field in body:
                    vals[field] = body[field]

            m2o_fields = {
                'categ_id':  'product.category',
                'uom_id':    'uom.uom',
                'uom_po_id': 'uom.uom',
            }
            for field, model in m2o_fields.items():
                if field in body:
                    if body[field] is None:
                        vals[field] = False
                    else:
                        related = request.env[model].sudo().browse(int(body[field]))
                        if not related.exists():
                            return http_response({'error': f'{field} not found'}, 400)
                        vals[field] = related.id

            if vals:
                rec.write(vals)

            return http_response({
                'id':             rec.id,
                'name':           rec.name,
                'default_code':   rec.default_code or '',
                'type':           rec.type,
                'list_price':     rec.list_price,
                'standard_price': rec.standard_price,
                'categ_id':       rec.categ_id.id if rec.categ_id else None,
                'categ_name':     rec.categ_id.name if rec.categ_id else None,
                'uom_id':         rec.uom_id.id if rec.uom_id else None,
                'uom_name':       rec.uom_id.name if rec.uom_id else None,
                'tracking':       rec.tracking,
                'active':         rec.active,
            })

        except Exception as e:
            return http_response({'error': str(e)}, 500)


class CategoryUpdateController(http.Controller):

    @http.route('/api/v1/categories/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_category(self, rec_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
            rec = request.env['product.category'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            vals = {}
            if 'name' in body:
                vals['name'] = body['name']
            if 'parent_id' in body:
                if body['parent_id'] is None:
                    vals['parent_id'] = False
                else:
                    parent = request.env['product.category'].sudo().browse(int(body['parent_id']))
                    if not parent.exists():
                        return http_response({'error': 'parent_id not found'}, 400)
                    vals['parent_id'] = parent.id

            if vals:
                rec.write(vals)

            return http_response({
                'id':            rec.id,
                'name':          rec.name,
                'complete_name': rec.complete_name,
                'parent_id':     rec.parent_id.id if rec.parent_id else None,
                'parent_name':   rec.parent_id.name if rec.parent_id else None,
            })

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.quant  (on-hand inventory with lot / expiry info)
# ─────────────────────────────────────────────────────────────────────────────

class QuantController(http.Controller):

    @http.route('/api/v1/stock/quants', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.quant'].sudo().search([
            ('location_id.usage', '=', 'internal'),
        ])
        data = []
        for rec in records:
            data.append({
                'id':                   rec.id,
                'product_id':           rec.product_id.id if rec.product_id else None,
                'product_name':         rec.product_id.name if rec.product_id else None,
                'product_default_code': rec.product_id.default_code or '' if rec.product_id else '',
                'product_uom_id':       rec.product_uom_id.id if rec.product_uom_id else None,
                'product_uom_name':     rec.product_uom_id.name if rec.product_uom_id else None,
                'location_id':          rec.location_id.id if rec.location_id else None,
                'location_name':        rec.location_id.complete_name if rec.location_id else None,
                'lot_id':               rec.lot_id.id if rec.lot_id else None,
                'lot_name':             rec.lot_id.name if rec.lot_id else None,
                'expiration_date':      str(rec.lot_id.expiration_date) if rec.lot_id and rec.lot_id.expiration_date else None,
                'quantity':             rec.quantity,
                'reserved_quantity':    rec.reserved_quantity,
                'available_quantity':   rec.available_quantity,
                'inventory_quantity':   rec.inventory_quantity,
                'in_date':              str(rec.in_date) if rec.in_date else None,
                'company_id':           rec.company_id.id if rec.company_id else None,
                'company_name':         rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/stock/quants/adjust', type='http', auth='user', methods=['POST'], csrf=False)
    def adjust_quantity(self, **kw):
        """
        Inventory adjustment — sets the on-hand quantity of a product at a location.
        Body: { product_id, location_id, quantity, lot_id? }
        Equivalent to Odoo's "Update Quantity" button on stock.quant.
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)

        product_id  = body.get('product_id')
        location_id = body.get('location_id')
        quantity    = body.get('quantity')
        lot_id      = body.get('lot_id')

        if not product_id or not location_id or quantity is None:
            return http_response({'error': 'product_id, location_id and quantity are required'}, 400)

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            return http_response({'error': 'quantity must be a number'}, 400)

        try:
            env = request.env['stock.quant'].sudo()
            domain = [
                ('product_id', '=', product_id),
                ('location_id', '=', location_id),
            ]
            if lot_id:
                domain.append(('lot_id', '=', lot_id))
            quants = env.search(domain)

            if quants:
                quant = quants[0]
            else:
                quant = env.create({
                    'product_id':  product_id,
                    'location_id': location_id,
                    'lot_id':      lot_id or False,
                    'quantity':    0,
                })

            quant.write({'inventory_quantity': quantity})
            quant.with_context(inventory_mode=True).action_apply_inventory()

            return http_response({
                'id':                  quant.id,
                'product_id':          quant.product_id.id,
                'product_name':        quant.product_id.name,
                'location_id':         quant.location_id.id,
                'location_name':       quant.location_id.complete_name,
                'lot_id':              quant.lot_id.id if quant.lot_id else None,
                'lot_name':            quant.lot_id.name if quant.lot_id else None,
                'quantity':            quant.quantity,
                'available_quantity':  quant.available_quantity,
            })
        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.warehouse
# ─────────────────────────────────────────────────────────────────────────────

class WarehouseController(http.Controller):

    @http.route('/api/v1/stock/warehouses', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.warehouse'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':                     rec.id,
                'name':                   rec.name,
                'code':                   rec.code,
                'partner_id':             rec.partner_id.id if rec.partner_id else None,
                'partner_name':           rec.partner_id.name if rec.partner_id else None,
                'lot_stock_id':           rec.lot_stock_id.id if rec.lot_stock_id else None,
                'lot_stock_name':         rec.lot_stock_id.complete_name if rec.lot_stock_id else None,
                'view_location_id':       rec.view_location_id.id if rec.view_location_id else None,
                'wh_input_stock_loc_id':  rec.wh_input_stock_loc_id.id if rec.wh_input_stock_loc_id else None,
                'wh_output_stock_loc_id': rec.wh_output_stock_loc_id.id if rec.wh_output_stock_loc_id else None,
                'reception_steps':        rec.reception_steps,
                'delivery_steps':         rec.delivery_steps,
                'in_type_id':             rec.in_type_id.id if rec.in_type_id else None,
                'out_type_id':            rec.out_type_id.id if rec.out_type_id else None,
                'int_type_id':            rec.int_type_id.id if rec.int_type_id else None,
                'company_id':             rec.company_id.id if rec.company_id else None,
                'company_name':           rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.picking  — CREATE + VALIDATE
# ─────────────────────────────────────────────────────────────────────────────

class PickingCreateController(http.Controller):

    @http.route('/api/v1/stock/pickings', type='http', auth='user', methods=['POST'], csrf=False)
    def create_picking(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            for required in ('picking_type_id', 'location_id', 'location_dest_id', 'moves'):
                if not body.get(required):
                    return http_response({'error': f'{required} is required'}, 400)

            picking_type = request.env['stock.picking.type'].sudo().browse(int(body['picking_type_id']))
            if not picking_type.exists():
                return http_response({'error': 'picking_type_id not found'}, 400)

            location_src = request.env['stock.location'].sudo().browse(int(body['location_id']))
            if not location_src.exists():
                return http_response({'error': 'location_id not found'}, 400)

            location_dst = request.env['stock.location'].sudo().browse(int(body['location_dest_id']))
            if not location_dst.exists():
                return http_response({'error': 'location_dest_id not found'}, 400)

            vals = {
                'picking_type_id':  picking_type.id,
                'location_id':      location_src.id,
                'location_dest_id': location_dst.id,
            }

            for field in ('origin', 'note', 'scheduled_date', 'date_deadline'):
                if body.get(field):
                    vals[field] = body[field]

            if body.get('partner_id'):
                partner = request.env['res.partner'].sudo().browse(int(body['partner_id']))
                if partner.exists():
                    vals['partner_id'] = partner.id

            move_vals_list = []
            for i, move in enumerate(body['moves']):
                if not move.get('product_id'):
                    return http_response({'error': f'moves[{i}]: product_id is required'}, 400)
                product = request.env['product.product'].sudo().browse(int(move['product_id']))
                if not product.exists():
                    return http_response({'error': f'moves[{i}]: product_id not found'}, 400)

                qty = float(move.get('quantity', move.get('product_uom_qty', 1)))
                move_vals_list.append((0, 0, {
                    'name':             product.display_name,
                    'product_id':       product.id,
                    'product_uom_qty':  qty,
                    'quantity':         qty,
                    'product_uom':      product.uom_id.id,
                    'location_id':      location_src.id,
                    'location_dest_id': location_dst.id,
                }))

            vals['move_ids'] = move_vals_list
            rec = request.env['stock.picking'].sudo().create(vals)

            return http_response({
                'id':                 rec.id,
                'name':               rec.name,
                'state':              rec.state,
                'picking_type_id':    rec.picking_type_id.id,
                'picking_type_name':  rec.picking_type_id.name,
                'location_id':        rec.location_id.id,
                'location_name':      rec.location_id.complete_name,
                'location_dest_id':   rec.location_dest_id.id,
                'location_dest_name': rec.location_dest_id.complete_name,
                'move_ids_count':     len(rec.move_ids),
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


class PickingValidateController(http.Controller):

    @http.route('/api/v1/stock/pickings/<int:rec_id>/validate', type='http', auth='user', methods=['POST'], csrf=False)
    def validate_picking(self, rec_id, **kw):
        try:
            rec = request.env['stock.picking'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state == 'done':
                return http_response({'error': 'picking is already done'}, 400)
            if rec.state == 'cancel':
                return http_response({'error': 'picking is cancelled'}, 400)

            body = json.loads(request.httprequest.data or '{}')
            if body.get('immediate_transfer', True):
                for move in rec.move_ids:
                    if move.quantity == 0:
                        move.quantity = move.product_uom_qty

            rec.button_validate()

            return http_response({
                'id':        rec.id,
                'name':      rec.name,
                'state':     rec.state,
                'date_done': str(rec.date_done) if rec.date_done else None,
            })

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.picking.type
# ─────────────────────────────────────────────────────────────────────────────

class PickingTypeController(http.Controller):

    @http.route('/api/v1/stock/picking-types', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.picking.type'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            data.append({
                'id':                           rec.id,
                'name':                         rec.name,
                'code':                         rec.code,
                'warehouse_id':                 rec.warehouse_id.id if rec.warehouse_id else None,
                'warehouse_name':               rec.warehouse_id.name if rec.warehouse_id else None,
                'default_location_src_id':      rec.default_location_src_id.id if rec.default_location_src_id else None,
                'default_location_dest_id':     rec.default_location_dest_id.id if rec.default_location_dest_id else None,
                'default_location_src_name':    rec.default_location_src_id.complete_name if rec.default_location_src_id else None,
                'default_location_dest_name':   rec.default_location_dest_id.complete_name if rec.default_location_dest_id else None,
                'sequence_code':                rec.sequence_code,
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.lot  (batch / serial / lot tracking)
# ─────────────────────────────────────────────────────────────────────────────

class LotController(http.Controller):

    @http.route('/api/v1/stock/lots', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.lot'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':               rec.id,
                'name':             rec.name,
                'ref':              rec.ref or '',
                'product_id':       rec.product_id.id if rec.product_id else None,
                'product_name':     rec.product_id.name if rec.product_id else None,
                'product_uom_id':   rec.product_uom_id.id if rec.product_uom_id else None,
                'product_uom_name': rec.product_uom_id.name if rec.product_uom_id else None,
                'expiration_date':  str(rec.expiration_date) if rec.expiration_date else None,
                'use_date':         str(rec.use_date) if rec.use_date else None,
                'removal_date':     str(rec.removal_date) if rec.removal_date else None,
                'alert_date':       str(rec.alert_date) if rec.alert_date else None,
                'note':             rec.note or '',
                'product_qty':      rec.product_qty,
                'company_id':       rec.company_id.id if rec.company_id else None,
                'company_name':     rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/stock/lots', type='http', auth='user', methods=['POST'], csrf=False)
    def create_lot(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            if not body.get('name'):
                return http_response({'error': 'name is required'}, 400)
            if not body.get('product_id'):
                return http_response({'error': 'product_id is required'}, 400)

            product = request.env['product.product'].sudo().browse(int(body['product_id']))
            if not product.exists():
                return http_response({'error': 'product_id not found'}, 400)

            vals = {
                'name':       body['name'],
                'product_id': product.id,
            }

            for field in ('ref', 'expiration_date', 'use_date', 'removal_date', 'alert_date', 'note'):
                if body.get(field):
                    vals[field] = body[field]

            if body.get('company_id'):
                company = request.env['res.company'].sudo().browse(int(body['company_id']))
                if company.exists():
                    vals['company_id'] = company.id

            rec = request.env['stock.lot'].sudo().create(vals)

            return http_response({
                'id':              rec.id,
                'name':            rec.name,
                'ref':             rec.ref or '',
                'product_id':      rec.product_id.id,
                'product_name':    rec.product_id.name,
                'expiration_date': str(rec.expiration_date) if rec.expiration_date else None,
                'use_date':        str(rec.use_date) if rec.use_date else None,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  hr.employee
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeController(http.Controller):

    @http.route('/api/v1/hr/employees', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.employee'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            data.append({
                'id':              rec.id,
                'name':            rec.name,
                'job_title':       rec.job_title or '',
                'job_id':          rec.job_id.id if rec.job_id else None,
                'job_name':        rec.job_id.name if rec.job_id else None,
                'department_id':   rec.department_id.id if rec.department_id else None,
                'department_name': rec.department_id.name if rec.department_id else None,
                'parent_id':       rec.parent_id.id if rec.parent_id else None,
                'parent_name':     rec.parent_id.name if rec.parent_id else None,
                'work_email':      rec.work_email or '',
                'work_phone':      rec.work_phone or '',
                'user_id':         rec.user_id.id if rec.user_id else None,
                'user_name':       rec.user_id.name if rec.user_id else None,
                'company_id':      rec.company_id.id if rec.company_id else None,
                'company_name':    rec.company_id.name if rec.company_id else None,
                'image_url':       '/web/image/hr.employee/%d/image_1920' % rec.id if rec.image_1920 else '',
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  hr.department
# ─────────────────────────────────────────────────────────────────────────────

class DepartmentController(http.Controller):

    @http.route('/api/v1/departments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.department'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            data.append({
                'id':            rec.id,
                'name':          rec.name,
                'complete_name': rec.complete_name,
                'parent_id':     rec.parent_id.id if rec.parent_id else None,
                'parent_name':   rec.parent_id.name if rec.parent_id else None,
                'manager_id':    rec.manager_id.id if rec.manager_id else None,
                'manager_name':  rec.manager_id.name if rec.manager_id else None,
                'member_ids':    rec.member_ids.ids,
                'child_ids':     rec.child_ids.ids,
                'company_id':    rec.company_id.id if rec.company_id else None,
                'company_name':  rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  res.partner  — vendors only
# ─────────────────────────────────────────────────────────────────────────────

class VendorController(http.Controller):

    @http.route('/api/v1/partners/vendors', type='http', auth='user', methods=['GET'], csrf=False)
    def get_vendors(self, **kw):
        records = request.env['res.partner'].sudo().search([
            ('supplier_rank', '>', 0),
            ('active', '=', True),
        ])
        data = []
        for rec in records:
            data.append({
                'id':            rec.id,
                'name':          rec.name,
                'ref':           rec.ref or '',
                'email':         rec.email or '',
                'phone':         rec.phone or '',
                'mobile':        rec.mobile or '',
                'street':        rec.street or '',
                'city':          rec.city or '',
                'country_id':    rec.country_id.id if rec.country_id else None,
                'country_name':  rec.country_id.name if rec.country_id else None,
                'vat':           rec.vat or '',
                'supplier_rank': rec.supplier_rank,
                'company_type':  rec.company_type,
                'parent_id':     rec.parent_id.id if rec.parent_id else None,
                'parent_name':   rec.parent_id.name if rec.parent_id else None,
                'image_url':     '/web/image/res.partner/%d/image_1920' % rec.id if rec.image_1920 else '',
            })
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  purchase.order  — CREATE + CONFIRM
# ─────────────────────────────────────────────────────────────────────────────

class PurchaseOrderCreateController(http.Controller):

    @http.route('/api/v1/purchase/orders', type='http', auth='user', methods=['POST'], csrf=False)
    def create_order(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            if not body.get('partner_id'):
                return http_response({'error': 'partner_id is required'}, 400)
            if not body.get('lines'):
                return http_response({'error': 'lines is required and must not be empty'}, 400)

            partner = request.env['res.partner'].sudo().browse(int(body['partner_id']))
            if not partner.exists():
                return http_response({'error': 'partner_id not found'}, 400)

            vals = {'partner_id': partner.id}

            for field in ('origin', 'partner_ref', 'date_order', 'date_planned', 'notes'):
                if body.get(field):
                    vals[field] = body[field]

            if body.get('currency_id'):
                currency = request.env['res.currency'].sudo().browse(int(body['currency_id']))
                if currency.exists():
                    vals['currency_id'] = currency.id

            now_str = odoo_fields.Datetime.to_string(odoo_fields.Datetime.now())
            line_vals_list = []
            for i, line in enumerate(body['lines']):
                if not line.get('product_id'):
                    return http_response({'error': f'lines[{i}]: product_id is required'}, 400)
                product = request.env['product.product'].sudo().browse(int(line['product_id']))
                if not product.exists():
                    return http_response({'error': f'lines[{i}]: product_id not found'}, 400)

                qty = float(line.get('product_qty', 1))
                price = float(line.get('price_unit', product.standard_price))
                uom_id = product.uom_id.id

                if line.get('uom_id'):
                    uom = request.env['uom.uom'].sudo().browse(int(line['uom_id']))
                    if uom.exists():
                        uom_id = uom.id

                line_vals_list.append((0, 0, {
                    'product_id':   product.id,
                    'name':         product.display_name,
                    'product_qty':  qty,
                    'price_unit':   price,
                    'product_uom':  uom_id,
                    'date_planned': line.get('date_planned') or body.get('date_planned') or now_str,
                }))

            vals['order_line'] = line_vals_list
            rec = request.env['purchase.order'].sudo().create(vals)

            return http_response({
                'id':            rec.id,
                'name':          rec.name,
                'state':         rec.state,
                'partner_id':    rec.partner_id.id,
                'partner_name':  rec.partner_id.name,
                'amount_total':  rec.amount_total,
                'currency_name': rec.currency_id.name if rec.currency_id else None,
                'date_order':    str(rec.date_order) if rec.date_order else None,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


class PurchaseOrderConfirmController(http.Controller):

    @http.route('/api/v1/purchase/orders/<int:rec_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm_order(self, rec_id, **kw):
        try:
            rec = request.env['purchase.order'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state not in ('draft', 'sent'):
                return http_response({'error': f'cannot confirm order in state: {rec.state}'}, 400)

            rec.button_confirm()

            return http_response({
                'id':           rec.id,
                'name':         rec.name,
                'state':        rec.state,
                'date_approve': str(rec.date_approve) if rec.date_approve else None,
            })

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  employee.purchase.requisition  — workflow actions
# ─────────────────────────────────────────────────────────────────────────────

class RequisitionActionController(http.Controller):

    @http.route('/api/v1/purchase/requisitions/<int:rec_id>/approve', type='http', auth='user', methods=['POST'], csrf=False)
    def approve_requisition(self, rec_id, **kw):
        try:
            rec = request.env['employee.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            if rec.state in ('new', 'waiting_department_approval'):
                if hasattr(rec, 'action_department_approval'):
                    rec.action_department_approval()
                else:
                    rec.write({'state': 'waiting_head_approval'})
            elif rec.state == 'waiting_head_approval':
                if hasattr(rec, 'action_head_approval'):
                    rec.action_head_approval()
                else:
                    rec.write({'state': 'approved'})
            else:
                return http_response({'error': f'cannot approve requisition in state: {rec.state}'}, 400)

            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})

        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/requisitions/<int:rec_id>/cancel', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel_requisition(self, rec_id, **kw):
        try:
            rec = request.env['employee.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state == 'cancelled':
                return http_response({'error': 'requisition is already cancelled'}, 400)

            if hasattr(rec, 'action_cancel'):
                rec.action_cancel()
            else:
                rec.write({'state': 'cancelled'})

            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})

        except Exception as e:
            return http_response({'error': str(e)}, 500)


# ─────────────────────────────────────────────────────────────────────────────
#  inventory dashboard  — aggregated KPIs
# ─────────────────────────────────────────────────────────────────────────────

class DashboardController(http.Controller):

    @http.route('/api/v1/inventory/dashboard', type='http', auth='user', methods=['GET'], csrf=False)
    def get_dashboard(self, **kw):
        env = request.env

        total_products = env['product.template'].sudo().search_count([
            ('type', '=', 'product'), ('active', '=', True),
        ])

        quants = env['stock.quant'].sudo().search([('location_id.usage', '=', 'internal')])
        total_qty = sum(quants.mapped('quantity'))

        below_safety_ids = {q.product_id.id for q in quants if q.quantity <= 0}
        below_safety_count = len(below_safety_ids)

        today = date.today()
        in_30 = today + timedelta(days=30)
        expiring_count = env['stock.lot'].sudo().search_count([
            ('expiration_date', '!=', False),
            ('expiration_date', '>=', str(today)),
            ('expiration_date', '<=', str(in_30)),
        ])

        today_start = odoo_fields.Datetime.to_string(
            odoo_fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        todays_movements = env['stock.picking'].sudo().search_count([
            ('state', '=', 'done'),
            ('date_done', '>=', today_start),
        ])

        pending_requisitions = env['employee.purchase.requisition'].sudo().search_count([
            ('state', 'in', ['new', 'waiting_department_approval', 'waiting_head_approval']),
        ])

        pending_pos = env['purchase.order'].sudo().search_count([
            ('state', 'in', ['draft', 'sent']),
        ])

        return http_response({
            'total_products':       total_products,
            'total_qty_onhand':     total_qty,
            'below_safety_count':   below_safety_count,
            'expiring_soon_count':  expiring_count,
            'todays_movements':     todays_movements,
            'pending_requisitions': pending_requisitions,
            'pending_pos':          pending_pos,
        })


# ─────────────────────────────────────────────────────────────────────────────
#  material.purchase.requisition
#  model: material.purchase.requisition  |  lines: material.purchase.requisition.line
#  route prefix: /api/v1/purchase/cr-requisitions
# ─────────────────────────────────────────────────────────────────────────────

class CrRequisitionController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['material.purchase.requisition'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':                           rec.id,
                'name':                         rec.name,
                'state':                        rec.state,
                # state: new / waiting_department_approval / waiting_ir_approval
                #        approved / purchase_order_created / received / rejected
                'request_action':               rec.request_action or '',
                # request_action: purchase order / internal picking
                'reason_for_requisition':       rec.reason_for_requisition or '',
                'reason_for_rejection':         rec.reason_for_rejection or '',
                'employee_id':                  rec.employee_id.id if rec.employee_id else None,
                'employee_name':                rec.employee_id.name if rec.employee_id else None,
                'department_id':                rec.department_id.id if rec.department_id else None,
                'department_name':              rec.department_id.name if rec.department_id else None,
                'requisition_responsible':      rec.requisition_responsible.id if rec.requisition_responsible else None,
                'requisition_responsible_name': rec.requisition_responsible.name if rec.requisition_responsible else None,
                'confirmed_by_id':              rec.confirmed_by_id.id if rec.confirmed_by_id else None,
                'confirmed_by_name':            rec.confirmed_by_id.name if rec.confirmed_by_id else None,
                'department_manager_id':        rec.department_manager_id.id if rec.department_manager_id else None,
                'department_manager_name':      rec.department_manager_id.name if rec.department_manager_id else None,
                'approved_id':                  rec.approved_id.id if rec.approved_id else None,
                'approved_name':                rec.approved_id.name if rec.approved_id else None,
                'rejected_id':                  rec.rejected_id.id if rec.rejected_id else None,
                'rejected_name':                rec.rejected_id.name if rec.rejected_id else None,
                'requisition_date':             str(rec.requisition_date) if rec.requisition_date else None,
                'requisition_deadline':         str(rec.requisition_deadline) if rec.requisition_deadline else None,
                'received_date':                str(rec.received_date) if rec.received_date else None,
                'confirmed_date':               str(rec.confirmed_date) if rec.confirmed_date else None,
                'department_approval_date':     str(rec.department_approval_date) if rec.department_approval_date else None,
                'approved_date':                str(rec.approved_date) if rec.approved_date else None,
                'rejected_date':                str(rec.rejected_date) if rec.rejected_date else None,
                'source_location_id':           rec.source_location_id.id if rec.source_location_id else None,
                'source_location_name':         rec.source_location_id.complete_name if rec.source_location_id else None,
                'destination_location_id':      rec.destination_location_id.id if rec.destination_location_id else None,
                'destination_location_name':    rec.destination_location_id.complete_name if rec.destination_location_id else None,
                'picking_type_id':              rec.picking_type_id.id if rec.picking_type_id else None,
                'picking_type_name':            rec.picking_type_id.name if rec.picking_type_id else None,
                'purchase_count':               rec.purchase_count,
                'internal_transfer_count':      rec.internal_transfer_count,
                'company_id':                   rec.company_id.id if rec.company_id else None,
                'company_name':                 rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)

        lines = []
        for line in rec.requisition_line_ids:
            lines.append({
                'id':               line.id,
                'product_id':       line.product_id.id if line.product_id else None,
                'product_name':     line.product_id.name if line.product_id else None,
                'default_code':     line.product_id.default_code or '' if line.product_id else '',
                'qty':              line.qty,
                'uom_id':           line.uom_id.id if line.uom_id else None,
                'uom_name':         line.uom_id.name if line.uom_id else None,
                'partner_id':       line.partner_id.id if line.partner_id else None,
                'partner_name':     line.partner_id.name if line.partner_id else None,
                'requisition_type': line.requisition_type if hasattr(line, 'requisition_type') else '',
            })

        data = {
            'id':                           rec.id,
            'name':                         rec.name,
            'state':                        rec.state,
            'request_action':               rec.request_action or '',
            'reason_for_requisition':       rec.reason_for_requisition or '',
            'reason_for_rejection':         rec.reason_for_rejection or '',
            'employee_id':                  rec.employee_id.id if rec.employee_id else None,
            'employee_name':                rec.employee_id.name if rec.employee_id else None,
            'department_id':                rec.department_id.id if rec.department_id else None,
            'department_name':              rec.department_id.name if rec.department_id else None,
            'requisition_responsible':      rec.requisition_responsible.id if rec.requisition_responsible else None,
            'requisition_responsible_name': rec.requisition_responsible.name if rec.requisition_responsible else None,
            'confirmed_by_id':              rec.confirmed_by_id.id if rec.confirmed_by_id else None,
            'confirmed_by_name':            rec.confirmed_by_id.name if rec.confirmed_by_id else None,
            'department_manager_id':        rec.department_manager_id.id if rec.department_manager_id else None,
            'department_manager_name':      rec.department_manager_id.name if rec.department_manager_id else None,
            'approved_id':                  rec.approved_id.id if rec.approved_id else None,
            'approved_name':                rec.approved_id.name if rec.approved_id else None,
            'rejected_id':                  rec.rejected_id.id if rec.rejected_id else None,
            'rejected_name':                rec.rejected_id.name if rec.rejected_id else None,
            'requisition_date':             str(rec.requisition_date) if rec.requisition_date else None,
            'requisition_deadline':         str(rec.requisition_deadline) if rec.requisition_deadline else None,
            'received_date':                str(rec.received_date) if rec.received_date else None,
            'confirmed_date':               str(rec.confirmed_date) if rec.confirmed_date else None,
            'department_approval_date':     str(rec.department_approval_date) if rec.department_approval_date else None,
            'approved_date':                str(rec.approved_date) if rec.approved_date else None,
            'rejected_date':                str(rec.rejected_date) if rec.rejected_date else None,
            'source_location_id':           rec.source_location_id.id if rec.source_location_id else None,
            'source_location_name':         rec.source_location_id.complete_name if rec.source_location_id else None,
            'destination_location_id':      rec.destination_location_id.id if rec.destination_location_id else None,
            'destination_location_name':    rec.destination_location_id.complete_name if rec.destination_location_id else None,
            'picking_type_id':              rec.picking_type_id.id if rec.picking_type_id else None,
            'picking_type_name':            rec.picking_type_id.name if rec.picking_type_id else None,
            'purchase_count':               rec.purchase_count,
            'internal_transfer_count':      rec.internal_transfer_count,
            'company_id':                   rec.company_id.id if rec.company_id else None,
            'company_name':                 rec.company_id.name if rec.company_id else None,
            'requisition_line_ids':         lines,
        }
        return http_response(data)


class CrRequisitionCreateController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions', type='http', auth='user', methods=['POST'], csrf=False)
    def create_cr_requisition(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')

            if not body.get('employee_id'):
                return http_response({'error': 'employee_id is required'}, 400)
            if not body.get('lines'):
                return http_response({'error': 'lines is required and must not be empty'}, 400)

            employee = request.env['hr.employee'].sudo().browse(int(body['employee_id']))
            if not employee.exists():
                return http_response({'error': 'employee_id not found'}, 400)

            vals = {'employee_id': employee.id}

            for field in ('reason_for_requisition', 'request_action',
                          'requisition_date', 'requisition_deadline'):
                if body.get(field):
                    vals[field] = body[field]

            if body.get('department_id'):
                dept = request.env['hr.department'].sudo().browse(int(body['department_id']))
                if dept.exists():
                    vals['department_id'] = dept.id

            if body.get('requisition_responsible'):
                user = request.env['res.users'].sudo().browse(int(body['requisition_responsible']))
                if user.exists():
                    vals['requisition_responsible'] = user.id

            VALID_TYPES = ('purchase_order', 'internal_transfer', 'purchase order', 'internal picking')
            line_vals_list = []
            for i, line in enumerate(body['lines']):
                if not line.get('product_id'):
                    return http_response({'error': f'lines[{i}]: product_id is required'}, 400)
                product = request.env['product.product'].sudo().browse(int(line['product_id']))
                if not product.exists():
                    return http_response({'error': f'lines[{i}]: product_id not found'}, 400)

                qty = float(line.get('qty', line.get('quantity', 1)))
                line_val = {
                    'product_id': product.id,
                    'qty':        qty,
                }

                if line.get('uom_id'):
                    uom = request.env['uom.uom'].sudo().browse(int(line['uom_id']))
                    if uom.exists():
                        line_val['uom_id'] = uom.id

                if line.get('partner_id'):
                    partner = request.env['res.partner'].sudo().browse(int(line['partner_id']))
                    if partner.exists():
                        line_val['partner_id'] = partner.id

                if line.get('requisition_type'):
                    line_val['requisition_type'] = line['requisition_type']

                line_vals_list.append((0, 0, line_val))

            vals['requisition_line_ids'] = line_vals_list
            rec = request.env['material.purchase.requisition'].sudo().create(vals)

            return http_response({
                'id':          rec.id,
                'name':        rec.name,
                'state':       rec.state,
                'employee_id': rec.employee_id.id,
                'employee_name': rec.employee_id.name,
                'department_id': rec.department_id.id if rec.department_id else None,
                'department_name': rec.department_id.name if rec.department_id else None,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


class CrRequisitionActionController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/approve', type='http', auth='user', methods=['POST'], csrf=False)
    def approve(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            if rec.state in ('new', 'waiting_department_approval'):
                if hasattr(rec, 'action_department_approval'):
                    rec.action_department_approval()
                else:
                    rec.write({'state': 'waiting_ir_approval'})
            elif rec.state == 'waiting_ir_approval':
                if hasattr(rec, 'action_ir_approval'):
                    rec.action_ir_approval()
                else:
                    rec.write({'state': 'approved'})
            else:
                return http_response({'error': f'cannot approve in state: {rec.state}'}, 400)

            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})

        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/cancel', type='http', auth='user', methods=['POST'], csrf=False)
    def cancel(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state == 'rejected':
                return http_response({'error': 'requisition is already rejected'}, 400)

            if hasattr(rec, 'action_reject'):
                rec.action_reject()
            else:
                rec.write({'state': 'rejected'})

            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})

        except Exception as e:
            return http_response({'error': str(e)}, 500)