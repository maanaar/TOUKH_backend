# -*- coding: utf-8 -*-
"""
Shared helpers for the inpatient "Open Bill": one persistent draft
sale.order per admission (saycare.admission.request.sale_order_id) that
every department appends billing lines to throughout the stay. The order is
only confirmed and invoiced once, at discharge
(AdmissionRequestController.discharge in admission_requests.py).

Consumables/medicines still have to leave the shelf the moment they are
dispensed, long before discharge, so their stock.move is created and
validated immediately (mirroring the existing manual-move pattern in
medications.py's legacy dispense path) and linked to the new sale.order.line
via sale_line_id. sale_stock's own procurement (_get_qty_procurement /
_action_launch_stock_rule) sums quantities off exactly that link, so when
action_confirm() finally runs at discharge it sees the line already fully
covered by a done move and does not schedule a second delivery for it.
"""
import logging
from .utils import assign_lots_for_move

_logger = logging.getLogger(__name__)


def ensure_admission_bill(admission, warehouse=None):
    """Get or create the admission's running (draft) sale.order."""
    env = admission.env
    so = admission.sale_order_id
    if so and so.exists() and so.state == 'draft':
        return so

    vals = {
        'partner_id': admission.patient_id.id,
        'origin':     f'Inpatient Bill / Admission {admission.id}',
    }
    if warehouse:
        vals['warehouse_id'] = warehouse.id

    so = env['sale.order'].sudo().create(vals)
    admission.sudo().write({'sale_order_id': so.id})
    return so


def _get_or_create_service_product(env, name):
    """A sale.order.line with no product_id blocks action_confirm() for the
    WHOLE order ('Some order lines are missing a product') — unlike an
    outpatient account.move.line, which tolerates one fine. So unlike
    _create_visit_invoice's product lookup (which just leaves product_id
    False on a miss), inpatient Open Bill lines must always resolve to a
    real product, auto-creating a minimal service one if nothing matches."""
    Product = env['product.product'].sudo()
    product = Product.search([('name', '=', name), ('type', '=', 'service')], limit=1)
    if product:
        return product
    template = env['product.template'].sudo().create({'name': name, 'type': 'service'})
    return template.product_variant_id


def add_bill_line(admission, product, qty, price_unit, name, warehouse=None, deliver_now=False):
    """Append a billing line to the admission's open sale.order.

    `product` must be a real product.product — pass one resolved via
    _get_or_create_service_product (or an actual stock item for
    deliver_now=True calls); a line with no product_id blocks action_confirm()
    for the whole order at discharge time.

    When deliver_now=True, also creates and validates the stock.move that
    physically moves the item right away (for consumables/medicines), linked
    to the new line via sale_line_id.
    """
    env = admission.env
    so = ensure_admission_bill(admission, warehouse)

    line = env['sale.order.line'].sudo().create({
        'order_id':        so.id,
        'product_id':      product.id,
        'product_uom_qty': qty,
        'product_uom_id':  product.uom_id.id,
        'price_unit':      price_unit,
        'name':            name,
    })

    move = None
    if deliver_now and warehouse and warehouse.lot_stock_id:
        dest_partner  = so.partner_shipping_id or so.partner_id
        location_dest = dest_partner.property_stock_customer if dest_partner else False
        if not location_dest:
            location_dest = env.ref('stock.stock_location_customers')
        # Not caught here on purpose: if the physical stock move fails, the
        # caller (e.g. dispatch_consumables) must not report a successful
        # dispense while stock never actually left the shelf.
        move = env['stock.move'].sudo().create({
            'product_id':       product.id,
            'product_uom_qty':  qty,
            'product_uom':      product.uom_id.id,
            'location_id':      warehouse.lot_stock_id.id,
            'location_dest_id': location_dest.id,
            'sale_line_id':     line.id,
            'origin':           so.name,
        })
        move._action_confirm()
        move._action_assign()
        assign_lots_for_move(move, warehouse.lot_stock_id)
        move.write({'quantity': qty, 'picked': True})
        move._action_done()

    return line, move


def admission_for_visit(visit):
    """The saycare.admission.request linked to this visit, if any."""
    if not visit or not visit.exists():
        return None
    return visit.env['saycare.admission.request'].sudo().search(
        [('visit_id', '=', visit.id)], limit=1
    ) or None


def is_admission_discharged(visit):
    """True only for an inpatient visit whose admission has already been
    discharged (its Open Bill is closed) — used to block new lab/rad/
    consumable charges from landing after the final invoice was generated."""
    if not visit or not visit.exists() or visit.visit_type != 'inpatient':
        return False
    admission = admission_for_visit(visit)
    return bool(admission and admission.worklist_stage == 'discharged')


def bill_service_orders(visit, records):
    """For inpatient visits, bill each record's linked saycare.service onto
    the admission's Open Bill — call right after creating lab/rad orders (or
    any other saycare.service-linked order), mirroring how outpatient visits
    bill the same services via visit.service_ids in _create_visit_invoice.
    No-ops for outpatient/emergency/consultation visits, which keep billing
    through the existing visit-level invoice instead."""
    if not visit or not visit.exists() or visit.visit_type != 'inpatient':
        return
    admission = admission_for_visit(visit)
    if not admission or admission.worklist_stage == 'discharged':
        return
    env = visit.env

    from .visits import service_charge_items

    for rec in records:
        svc = rec.service_id
        if svc:
            product = svc.product_id.product_variant_id if svc.product_id else None
            if not product:
                product = _get_or_create_service_product(env, svc.name)
            for name, price in service_charge_items(visit, svc):
                add_bill_line(admission, product, 1, price, name, deliver_now=False)
            continue

        # No saycare.service link — most lab tests only ever resolve here,
        # since /saycare/api/lab-tests (and part of the rad catalog) is
        # sourced straight from product.template, a separate id space with
        # no saycare.service counterpart to carry an insurance-split price.
        # Bill the product's own price as a single line instead of dropping
        # the charge silently.
        tmpl = getattr(rec, 'product_id', False)
        if not tmpl:
            continue
        product = tmpl.product_variant_id or _get_or_create_service_product(env, tmpl.name)
        name = getattr(rec, 'test_name', None) or getattr(rec, 'study_type', None) or tmpl.name
        add_bill_line(admission, product, 1, tmpl.list_price, name, deliver_now=False)
