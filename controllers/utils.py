# -*- coding: utf-8 -*-
import datetime
import json
from zoneinfo import ZoneInfo
from odoo import fields
from odoo.http import Response

_CAIRO_TZ = ZoneInfo('Africa/Cairo')


def local_day_bounds_utc(date_str):
    """Convert a plain 'YYYY-MM-DD' local (Cairo) calendar date into the
    [start, end) naive-UTC datetime bounds that match how Odoo actually
    stores Datetime fields. A date-range filter built by just parsing the
    string and comparing directly (no timezone conversion at all) silently
    excludes anything created after local midnight but before UTC midnight —
    e.g. a medication prescribed at 00:40 local (Cairo, UTC+2/+3) has
    prescribed_at stored as ~21:40-22:40 UTC the *previous* day, which a
    naive 'today' filter for the new local day would never match."""
    try:
        d = datetime.date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None
    start_local = datetime.datetime.combine(d, datetime.time.min, tzinfo=_CAIRO_TZ)
    end_local = start_local + datetime.timedelta(days=1)
    return (
        start_local.astimezone(ZoneInfo('UTC')).replace(tzinfo=None),
        end_local.astimezone(ZoneInfo('UTC')).replace(tzinfo=None),
    )


def assign_lots_for_move(move, source_location):
    """For a lot/serial-tracked product, Odoo's own reservation doesn't pick
    a lot on its own, and validating the move refuses to complete without
    one. Auto-assign the nearest-to-expire available lot at source_location
    (FEFO — same criterion the الأصناف المطلوبة transfer screen already uses),
    or, if this product's stock was never actually recorded under any lot at
    all (a real data gap seen on several catalog items — e.g. "حزام بطن"
    had 50 units on hand with zero stock.lot records ever created for it),
    auto-create one rather than hard-failing the dispense over a data-entry
    gap the person dispensing has no way to fix themselves."""
    env = move.env
    for ml in move.move_line_ids:
        product = ml.product_id
        if product.tracking == 'none' or ml.lot_id:
            continue
        quant = env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', '=', source_location.id),
            ('quantity', '>', 0),
            ('lot_id', '!=', False),
        ], order='id')
        quant = quant.sorted(
            lambda q: getattr(q.lot_id, 'expiration_date', False) or fields.Datetime.now()
        )[:1]
        if quant:
            ml.lot_id = quant.lot_id.id
        else:
            lot = env['stock.lot'].sudo().create({
                'product_id': product.id,
                'company_id': move.company_id.id,
            })
            ml.lot_id = lot.id


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
        # These are live dashboards/lists — never let the browser or an
        # intermediate proxy serve a stale cached copy of a GET response.
        headers=[('Cache-Control', 'no-store, no-cache, must-revalidate')],
    )


def _patient_dict(p):
    return {
        'id':                p.id,
        'name':              p.name or '',
        'first_name':        p.first_name or '',
        'second_name':       p.second_name or '',
        'third_name':        p.third_name or '',
        'last_name':         p.last_name or '',
        'mrn':               getattr(p, 'mrn', '') or '',
        'entry_permit_no':   getattr(p, 'x_entry_permit_no', '') or '',
        'patient_type':      p.patient_type or 'normal',
        'id_type':           p.id_type or 'national_id',
        'id_number':         p.id_number or '',
        'dob':               str(p.dob) if p.dob else None,
        'gender':            p.gender or '',
        'blood_type':        getattr(p, 'x_blood_type', '') or '',
        'mobile':            p.phone or '',
        'home_phone':        p.home_phone or '',
        'phone':             p.phone or '',
        'occupation':        p.occupation or '',
        'nationality':       p.country_id.name if p.country_id else '',
        'governorate':       p.governorate or '',
        'city':              p.city or '',
        'street':            p.street or '',
        'financial_class':   p.financial_class or 'cash',
        'insurance_company': p.insurance_company or '',
        'contract_entity':   p.contract_entity or '',
        # 'department_id':     getattr(p, 'last_department_id', False).id if getattr(p, 'last_department_id', False) else None,
        # 'floor_id':          getattr(p, 'last_floor_id', False).id if getattr(p, 'last_floor_id', False) else None,
        # 'room_id':           getattr(p, 'last_room_id', False).id if getattr(p, 'last_room_id', False) else None,
        # 'bed_id':            getattr(p, 'last_bed_id', False).id if getattr(p, 'last_bed_id', False) else None,
        'image_url':         '/web/image/res.partner/%d/image_1920' % p.id if p.image_1920 else '',
    }
