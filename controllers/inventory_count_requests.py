# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request
from .utils import _json

_logger = logging.getLogger(__name__)

_MODEL = 'saycare.inventory.count.request'
_LINE_MODEL = 'saycare.inventory.count.request.line'


def _load_body():
    try:
        return json.loads(request.httprequest.data or '{}'), None
    except json.JSONDecodeError:
        return None, _json({'error': 'invalid JSON'}, 400)


def _int_or_false(v):
    try:
        return int(v) if v not in (None, '', False) else False
    except (TypeError, ValueError):
        return False


# Requests created before the two-stage (member+chair) approval was collapsed
# into a single 'review' stage may still carry the old state values in the
# database — normalize them to 'review' the first time they're touched again,
# instead of requiring a manual data migration.
_LEGACY_REVIEW_STATES = ('review_member', 'review_chair')


def _normalize_legacy_state(rec):
    if rec.state in _LEGACY_REVIEW_STATES:
        rec.write({'state': 'review'})


def _snapshot_system_qty(env, product_id, location_id):
    """Sum of on-hand qty (quantity - reserved) for a product at a location
    and its sub-locations — same domain convention as controllers/stock.py."""
    if not product_id or not location_id:
        return 0.0
    quants = env['stock.quant'].sudo().search([
        ('product_id', '=', product_id),
        ('location_id', 'child_of', location_id),
    ])
    return sum((q.quantity - q.reserved_quantity) for q in quants)


def _resolve_variant(env, raw_id):
    """The React product pickers (searchProductsFast / getProductsByLocation) all
    search and return product.template ids — but stock.quant.product_id (and this
    line's product_id) is a product.product. Resolve the template's first variant;
    fine for the non-variant medical/consumable items this feature deals with."""
    if not raw_id:
        return None
    variant = env['product.product'].sudo().search([('product_tmpl_id', '=', raw_id)], limit=1)
    if variant:
        return variant
    # raw_id may already be a product.product id (e.g. a value read back from a
    # previously-saved line) — fall back to browsing it directly.
    product = env['product.product'].sudo().browse(raw_id)
    return product if product.exists() else None


def _build_line_vals(env, body_line, warehouse):
    raw_id = _int_or_false(body_line.get('productId') or body_line.get('product_id'))
    if not raw_id:
        return None

    product = _resolve_variant(env, raw_id)
    if not product:
        return None
    product_id = product.id

    location_id = _int_or_false(body_line.get('locationId') or body_line.get('location_id'))
    if not location_id and warehouse and warehouse.lot_stock_id:
        location_id = warehouse.lot_stock_id.id

    lot_id = _int_or_false(body_line.get('lotId') or body_line.get('lot_id'))
    uom_id = _int_or_false(body_line.get('uomId') or body_line.get('uom_id')) or product.uom_id.id

    try:
        actual_qty = float(body_line.get('actualQty', body_line.get('actual_qty', 0)) or 0)
    except (TypeError, ValueError):
        actual_qty = 0.0

    return {
        'product_id':  product_id,
        'location_id': location_id or False,
        'lot_id':      lot_id or False,
        'uom_id':      uom_id or False,
        'system_qty':  _snapshot_system_qty(env, product_id, location_id),
        'actual_qty':  actual_qty,
        'note':        body_line.get('note') or '',
    }


class InventoryCountRequestController(http.Controller):

    @http.route('/api/v1/inventory-count-requests', type='http', auth='user', methods=['GET'], csrf=False)
    def list_requests(self, scope='mine', user_id='', **kw):
        env = request.env
        domain = []

        if scope == 'committee':
            domain.append(('state', 'in', ('review',) + _LEGACY_REVIEW_STATES))
        else:
            uid = _int_or_false(user_id) or env.uid
            domain.append(('user_id', '=', uid))

        records = env[_MODEL].sudo().search(domain, order='create_date desc')
        for rec in records:
            _normalize_legacy_state(rec)
        return _json([r._to_dict(with_lines=False) for r in records])

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_request(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الجرد غير موجود'}, 404)
        _normalize_legacy_state(rec)
        return _json(rec._to_dict())

    @http.route('/api/v1/inventory-count-requests', type='http', auth='user', methods=['POST'], csrf=False)
    def create_request(self, **kw):
        env = request.env
        body, err = _load_body()
        if err:
            return err

        warehouse_id = _int_or_false(body.get('warehouseId') or body.get('warehouse_id'))
        if not warehouse_id:
            return _json({'error': 'المخزن مطلوب'}, 400)

        warehouse = env['stock.warehouse'].sudo().browse(warehouse_id)
        if not warehouse.exists():
            return _json({'error': 'المخزن غير موجود'}, 404)

        user_id = _int_or_false(body.get('userId') or body.get('user_id')) or env.uid

        line_vals = []
        for body_line in (body.get('lines') or []):
            vals = _build_line_vals(env, body_line, warehouse)
            if vals:
                line_vals.append((0, 0, vals))

        rec = env[_MODEL].sudo().create({
            'warehouse_id': warehouse.id,
            'user_id':      user_id,
            'date':         body.get('date') or fields.Date.context_today(env.user),
            'notes':        body.get('notes') or '',
            'line_ids':     line_vals,
        })

        if body.get('submit'):
            rec.write({'state': 'review'})

        return _json(rec._to_dict(), 201)

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_request(self, rec_id, **kw):
        env = request.env
        rec = env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الجرد غير موجود'}, 404)
        if rec.state not in ('draft', 'rejected'):
            return _json({'error': 'لا يمكن تعديل طلب بعد إرساله للجنة الاعتماد'}, 400)

        body, err = _load_body()
        if err:
            return err

        vals = {}
        warehouse = rec.warehouse_id
        if 'warehouseId' in body or 'warehouse_id' in body:
            warehouse_id = _int_or_false(body.get('warehouseId') or body.get('warehouse_id'))
            warehouse = env['stock.warehouse'].sudo().browse(warehouse_id)
            if not warehouse.exists():
                return _json({'error': 'المخزن غير موجود'}, 404)
            vals['warehouse_id'] = warehouse.id
        if 'date' in body:
            vals['date'] = body.get('date') or fields.Date.context_today(env.user)
        if 'notes' in body:
            vals['notes'] = body.get('notes') or ''

        if 'lines' in body:
            line_vals = [(5, 0, 0)]
            for body_line in (body.get('lines') or []):
                l_vals = _build_line_vals(env, body_line, warehouse)
                if l_vals:
                    line_vals.append((0, 0, l_vals))
            vals['line_ids'] = line_vals

        if rec.state == 'rejected' and not body.get('keepRejected'):
            vals['state'] = 'draft'

        if vals:
            rec.write(vals)
        return _json(rec._to_dict())

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_request(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if rec.exists():
            if rec.state not in ('draft', 'rejected'):
                return _json({'error': 'لا يمكن حذف طلب بعد إرساله للجنة الاعتماد'}, 400)
            rec.unlink()
        return _json({'ok': True})

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>/submit', type='http', auth='user', methods=['POST'], csrf=False)
    def submit_request(self, rec_id, **kw):
        rec = request.env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الجرد غير موجود'}, 404)
        if rec.state not in ('draft', 'rejected'):
            return _json({'error': 'الطلب في مرحلة اعتماد بالفعل'}, 400)
        if not rec.line_ids:
            return _json({'error': 'أضف صنفاً واحداً على الأقل قبل الإرسال'}, 400)

        rec.write({
            'state':             'review',
            'rejection_reason':  False,
            'rejected_at':       False,
        })
        return _json(rec._to_dict())

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>/approve', type='http', auth='user', methods=['POST'], csrf=False)
    def approve_request(self, rec_id, **kw):
        env = request.env
        rec = env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الجرد غير موجود'}, 404)

        body, err = _load_body()
        if err:
            return err
        approver_id = _int_or_false(body.get('userId') or body.get('user_id')) or env.uid

        _normalize_legacy_state(rec)
        if rec.state != 'review':
            return _json({'error': 'الطلب ليس بانتظار اعتماد اللجنة'}, 400)

        rec.write({
            'member_user_id':     approver_id,
            'member_approved_at': fields.Datetime.now(),
            'state':              'approved',
        })
        self._post_to_actual_inventory(rec)

        return _json(rec._to_dict())

    def _post_to_actual_inventory(self, rec):
        """Apply every counted line onto stock.quant — mirrors QuantController.adjust_quantity
        in main.py (Odoo's native "Update Quantity" / inventory-adjustment action)."""
        env = request.env
        Quant = env['stock.quant'].sudo()
        for line in rec.line_ids:
            if not line.product_id or not line.location_id:
                continue
            domain = [
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
            ]
            if line.lot_id:
                domain.append(('lot_id', '=', line.lot_id.id))
            quant = Quant.search(domain, limit=1)
            if not quant:
                quant = Quant.create({
                    'product_id':  line.product_id.id,
                    'location_id': line.location_id.id,
                    'lot_id':      line.lot_id.id if line.lot_id else False,
                    'quantity':    0,
                })
            quant.write({'inventory_quantity': line.actual_qty})
            quant.with_context(inventory_mode=True).action_apply_inventory()

        rec.write({
            'state':      'posted',
            'posted_at':  fields.Datetime.now(),
            'posted_ref': f'QI-{fields.Date.context_today(env.user)}-{rec.id}',
        })

    @http.route('/api/v1/inventory-count-requests/<int:rec_id>/reject', type='http', auth='user', methods=['POST'], csrf=False)
    def reject_request(self, rec_id, **kw):
        env = request.env
        rec = env[_MODEL].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الجرد غير موجود'}, 404)
        _normalize_legacy_state(rec)
        if rec.state != 'review':
            return _json({'error': 'الطلب ليس بانتظار اعتماد اللجنة'}, 400)

        body, err = _load_body()
        if err:
            return err
        reason = (body.get('reason') or '').strip()

        rec.write({
            'state':            'rejected',
            'rejection_reason': reason,
            'rejected_at':      fields.Datetime.now(),
        })
        return _json(rec._to_dict())
