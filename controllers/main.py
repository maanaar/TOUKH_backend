# -*- coding: utf-8 -*-
import json
import time
from datetime import date, timedelta
from odoo import http, fields as odoo_fields
from odoo.http import request, Response


def http_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False, default=str)
    return Response(body, status=status, mimetype='application/json')


def _location_covered(location, employee):
    """True if `location` is one of `employee.location_ids`, a descendant of
    one of them, or shares a warehouse with an assigned location that is that
    warehouse's own root stock location.

    The third case matters because a warehouse's department sub-locations
    ("عهدة مستلزمات...") are siblings of its root "Stock" location in the
    location tree (both live directly under the warehouse's view location),
    not descendants of "Stock" — a plain child_of check on the root location
    alone would never match any of them. stock.location.warehouse_id is a
    compute that already walks the correct (view_location_id-rooted) tree, so
    reusing it here is what makes "assign the whole warehouse" still cover
    every department under it, exactly as it did before per-location
    assignment replaced the old warehouse-level hr.employee.warehouse_ids.

    No linked hr.employee at all (e.g. a system/admin login not tied to a
    staff record) stays unrestricted. But an employee record that exists
    with zero location_ids is deliberately denied everything, not allowed
    through — an employee with no assignment yet must not be able to create,
    send, or receive طلبات صرف واستلام الأقسام for any location until an
    admin actually assigns one.
    """
    if not employee:
        return True
    if not location or not employee.location_ids:
        return False
    env = location.env
    if env['stock.location'].search_count([
        ('id', '=', location.id),
        ('id', 'child_of', employee.location_ids.ids),
    ]):
        return True
    location_warehouse = location.warehouse_id
    if not location_warehouse:
        return False
    return any(
        loc.warehouse_id == location_warehouse and loc.id == location_warehouse.lot_stock_id.id
        for loc in employee.location_ids
    )


def _normalize_ar_keyword(text):
    """Collapse Arabic spelling variants that get typed inconsistently
    depending on who entered the data and which keyboard they used:
    - alef forms (أ/إ/آ) vs bare alef (ا) — e.g. "أشعة" vs "اشعة"
    - ta marbuta (ة) vs ha (ه) — e.g. "الأشعة" vs "الاشعه"
    Matching on the normalized form means a caller only has to type one
    spelling and it still finds category names stored with another."""
    if not text:
        return ''
    for ch in ('أ', 'إ', 'آ'):
        text = text.replace(ch, 'ا')
    text = text.replace('ة', 'ه')
    return text.lower()


def _categ_ids_by_keyword(env, keyword):
    """product.category ids whose name, complete_name (full path) or
    name_ar contains keyword, matched after Arabic normalization (see
    _normalize_ar_keyword) so alef/ta-marbuta spelling differences between
    the caller and the DB don't cause a real match to be missed."""
    norm_kw = _normalize_ar_keyword(keyword)
    if not norm_kw:
        return []
    categs = env['product.category'].sudo().search([])
    return [
        c.id for c in categs
        if norm_kw in _normalize_ar_keyword(c.name or '')
        or norm_kw in _normalize_ar_keyword(c.complete_name or '')
        or norm_kw in _normalize_ar_keyword(getattr(c, 'name_ar', '') or '')
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  شاشة الأصناف والأدوية (/unit/inventory/items) — field mapping
#
#  The frontend form (ItemFormView + TabGeneralData/TabDrugData/TabServiceData)
#  uses its own key names for a few fields that already exist on product.template
#  under different names (added earlier for the native Odoo medicine tabs), and
#  a few enum values that don't line up 1:1. ITEMS_FIELD_ALIASES translates the
#  frontend's key to the real backend field; ITEMS_VALUE_TRANSFORMS additionally
#  remaps values where the two sides don't share the same vocabulary.
# ─────────────────────────────────────────────────────────────────────────────

ITEMS_FIELD_ALIASES = {
    'drug_generic':         'generic_name',
    'drug_form':             'dosage_form',
    'drug_strength':        'medicine_concentration',
    'drug_route':            'primary_route',
    'drug_route_secondary': 'secondary_route',
    'drug_atc':              'atc_code',
    'drug_rx':               'dispensing_category',
    'drug_usual_dose':      'usual_dose',
    'drug_max_dose':         'max_daily_dose',
    'drug_contraindications': 'contraindications',
    'drug_warnings':         'special_warnings',
    'drug_side_effects':    'side_effects',
    'sc_refrigeration':      'needs_refrigeration',
    'sc_hazardous':          'is_hazardous',
}

# Simple flat fields the items form collects that map 1:1 by name onto
# product.template (added in models/saycare_medicine.py).
ITEMS_SIMPLE_FIELDS = [
    'name_en',
    'main_category', 'sub_category', 'department', 'is_critical', 'needs_approval',
    'can_dispense', 'show_pharmacy', 'show_warehouse', 'show_purchase_req',
    'show_internal_transfer', 'needs_tracking', 'has_expiry', 'expiration_date', 'allow_fractions',
    'allow_partial',
    'tax_purchase', 'tax_sale', 'currency', 'price_include_tax',
    'origin_country', 'purchase_policy', 'min_purchase_qty',
    'default_warehouse', 'storage_location', 'bin_location', 'dispense_method',
    'reorder_point', 'safety_stock', 'min_qty', 'max_qty',
    'sc_heat', 'sc_light', 'sc_dry', 'sc_fragile', 'sc_flammable', 'sc_sterile',
    'expiry_months', 'storage_temp',
    'op_purchase_req', 'op_dispense_req', 'op_internal_transfer', 'op_pharmacy',
    'op_clinics', 'op_lab', 'op_radiology', 'op_physiotherapy', 'op_dashboard',
    'op_dispense_approval', 'op_transfer_approval', 'op_dept_dispense',
    'op_custody_dispense', 'op_consumed_on_use',
    'cost_center', 'analytic_account', 'acc_inventory', 'acc_expense',
    'acc_cogs', 'acc_income',
    'notes_internal', 'notes_warehouse', 'notes_user',
    'forced_price', 'similarity_type', 'drug_interactions',
    'service_duration', 'bookable',
]

# Enum values that don't share the same vocabulary between the items form and
# the (richer) native medicine fields.
_PREGNANCY_CAT_MAP = {'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'X': 'x'}
_LACTATION_MAP  = {'safe': 'safe', 'caution': 'caution', 'avoid': 'unsafe'}
_PEDIATRIC_MAP  = {'approved': 'safe', 'caution': 'caution', 'not_recommended': 'unsafe'}


def _apply_items_form_vals(body, vals):
    """Mutates `vals` in place with every items-form field found in `body`,
    applying name aliases and enum-value remaps as needed."""
    for field in ITEMS_SIMPLE_FIELDS:
        if field in body:
            vals[field] = body[field]

    for fe_key, be_key in ITEMS_FIELD_ALIASES.items():
        if fe_key in body:
            vals[be_key] = body[fe_key]

    if 'use_types' in body:
        val = body['use_types']
        vals['use_types'] = ','.join(val) if isinstance(val, list) else (val or '')

    if 'drug_pregnancy_cat' in body:
        vals['pregnancy_category'] = _PREGNANCY_CAT_MAP.get(body['drug_pregnancy_cat'], body['drug_pregnancy_cat'] or False) or False
    if 'drug_lactation' in body:
        vals['lactation_use'] = _LACTATION_MAP.get(body['drug_lactation'], body['drug_lactation'] or False) or False
    if 'drug_pediatric' in body:
        vals['pediatric_use'] = _PEDIATRIC_MAP.get(body['drug_pediatric'], body['drug_pediatric'] or False) or False

    for json_field in ('_packUnits', '_suppliers', '_attachments'):
        if json_field in body:
            backend_field = {'_packUnits': 'pack_units_json', '_suppliers': 'suppliers_json', '_attachments': 'attachments_json'}[json_field]
            vals[backend_field] = json.dumps(body[json_field] or [], ensure_ascii=False)

    if 'manufacturer' in body:
        vals['manufacturer'] = int(body['manufacturer']) if body['manufacturer'] else False
    if 'group_id' in body:
        vals['group_id'] = int(body['group_id']) if body['group_id'] else False
    for uom_field in ('uom_small', 'uom_mediumm', 'uom_largee'):
        if uom_field in body:
            vals[uom_field] = int(body[uom_field]) if body[uom_field] else False

    # Integer/float fields sent as '' from empty number inputs would fail write() —
    # normalize blanks to 0/False instead of letting them through as strings.
    for int_field in ('min_purchase_qty', 'reorder_point', 'safety_stock',
                      'min_qty', 'max_qty', 'expiry_months', 'storage_temp'):
        if int_field in vals and vals[int_field] in (None, ''):
            vals[int_field] = 0


def _packaging_options(rec):
    """Base uom_id plus each additional packaging in uom_ids (native
    product.template 'Packagings' field), price-converted through the
    packaging's factor against the base unit. This is the list dispense
    screens build the الوحدة dropdown from — deliberately narrower than
    every uom.uom in the system, since it only offers units the product is
    actually configured to be sold/dispensed in.
    """
    base_uom = rec.uom_id
    if not base_uom:
        return []
    options = [{'id': base_uom.id, 'name': base_uom.name, 'price': rec.list_price}]
    for uom in rec.uom_ids:
        ratio = (uom.factor / base_uom.factor) if base_uom._has_common_reference(uom) else None
        options.append({
            'id': uom.id,
            'name': uom.name,
            'price': rec.list_price * ratio if ratio is not None else rec.list_price,
        })
    return options


def _items_form_dict(rec):
    """Read side — mirrors _apply_items_form_vals(), returning the items-form
    field names the frontend expects (drug_*, use_types, sc_*, etc.)."""
    reverse_aliases = {be: fe for fe, be in ITEMS_FIELD_ALIASES.items()}
    data = {}
    for field in ITEMS_SIMPLE_FIELDS:
        data[field] = getattr(rec, field, False) or (0 if field in (
            'min_purchase_qty', 'reorder_point', 'safety_stock', 'min_qty',
            'max_qty', 'expiry_months', 'storage_temp',
        ) else False)
    for be_key, fe_key in reverse_aliases.items():
        data[fe_key] = getattr(rec, be_key, False) or False

    data['use_types'] = [v for v in (rec.use_types or '').split(',') if v]

    rev_pregnancy = {v: k for k, v in _PREGNANCY_CAT_MAP.items()}
    rev_lactation = {v: k for k, v in _LACTATION_MAP.items()}
    rev_pediatric = {v: k for k, v in _PEDIATRIC_MAP.items()}
    data['drug_pregnancy_cat'] = rev_pregnancy.get(rec.pregnancy_category, '')
    data['drug_lactation']     = rev_lactation.get(rec.lactation_use, '')
    data['drug_pediatric']     = rev_pediatric.get(rec.pediatric_use, '')

    try:
        data['_packUnits']  = json.loads(rec.pack_units_json) if rec.pack_units_json else []
    except (ValueError, TypeError):
        data['_packUnits'] = []
    try:
        data['_suppliers'] = json.loads(rec.suppliers_json) if rec.suppliers_json else []
    except (ValueError, TypeError):
        data['_suppliers'] = []
    try:
        data['_attachments'] = json.loads(rec.attachments_json) if rec.attachments_json else []
    except (ValueError, TypeError):
        data['_attachments'] = []

    data['manufacturer']      = rec.manufacturer.id if rec.manufacturer else None
    data['manufacturer_name'] = rec.manufacturer.name if rec.manufacturer else ''
    data['group_id']          = rec.group_id.id if rec.group_id else None
    data['group_name']        = rec.group_id.name if rec.group_id else ''
    data['uom_small']          = rec.uom_small.id if rec.uom_small else None
    data['uom_small_name']     = rec.uom_small.name if rec.uom_small else ''
    data['uom_mediumm']        = rec.uom_mediumm.id if rec.uom_mediumm else None
    data['uom_mediumm_name']   = rec.uom_mediumm.name if rec.uom_mediumm else ''
    data['uom_largee']         = rec.uom_largee.id if rec.uom_largee else None
    data['uom_largee_name']    = rec.uom_largee.name if rec.uom_largee else ''

    return data


# ─────────────────────────────────────────────────────────────────────────────
#  product.category
# ─────────────────────────────────────────────────────────────────────────────

class CategoryController(http.Controller):

    @http.route('/api/v1/categories', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        domain = []
        parent_name = kw.get('parent_name')
        if parent_name:
            domain = [('parent_id.name', 'ilike', parent_name)]
        records = request.env['product.category'].sudo().search(domain)
        data = []
        for rec in records:
            data.append({
                'id':                        rec.id,
                'name':                      rec.name,
                'name_ar':                   rec.name_ar if hasattr(rec, 'name_ar') else '',
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
            'property_stock_valuation_account_id':    rec.property_stock_valuation_account_id.id if rec.property_stock_valuation_account_id else None,
            'property_stock_journal':                 rec.property_stock_journal.id if rec.property_stock_journal else None,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  basket.model
# ─────────────────────────────────────────────────────────────────────────────

class BasketModel(http.Controller):

    @http.route('/api/basket/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env['product.template'].sudo().browse(rec_id).basket_table_id.ids
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        ids = []
        for re in rec:
            data = {
                'id': re.id,
                'serial_no': re.serial_no,
                'product_product_id': re.product_product_id.id if re.product_product_id else False,
                'uom_id': re.uom_id.id if re.uom_id else False,
                'barcode': re.barcode,
                'planned_qty': re.planned_qty,
                'price': re.price,
                'total_price': re.total_price,
            }
            ids.append(data)
        return http_response(ids)


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
                'factor':        rec.factor,
                'rounding':      rec.rounding,
                'active':        rec.active,
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
            'factor':        rec.factor,
            'rounding':      rec.rounding,
            'active':        rec.active,
        }
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  product.template
# ─────────────────────────────────────────────────────────────────────────────

class ProductController(http.Controller):

    @http.route('/api/v1/products', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, location_id='', categ_keyword='', term='', medicines_only='', limit='', **kw):
        domain = []
        if location_id:
            loc = request.env['stock.location'].sudo().browse(int(location_id))
            if loc.exists():
                quants = request.env['stock.quant'].sudo().search([
                    ('location_id', 'child_of', loc.id),
                ])
                # Odoo's search() silently excludes active=False records even
                # with an explicit 'id in [...]' domain — a product archived
                # after it was stocked (e.g. discontinued) would otherwise
                # vanish from here even though it still has real quantity on
                # hand and needs to stay dispensable until that stock is used up.
                domain = [
                    ('id', 'in', quants.mapped('product_id.product_tmpl_id').ids),
                    ('active', 'in', [True, False]),
                ]
            else:
                domain = [('id', '=', 0)]  # unknown location — no products, not "all products"
        if categ_keyword:
            # Matches on name, complete_name (full path — covers subcategories
            # like الأدوية's children) and name_ar, after Arabic normalization
            # so alef/ta-marbuta spelling differences don't hide a real match.
            domain += [('categ_id', 'in', _categ_ids_by_keyword(request.env, categ_keyword))]
        # أدوية checkbox on product.category, expanded to subcategories — computed
        # here (ahead of the search) so a term search can optionally be scoped to
        # medicines only; also reused below to tag is_medicines on every record.
        medicine_roots = request.env['product.category'].sudo().search([('is_medicines', '=', True)])
        medicine_categ_ids = set(
            request.env['product.category'].sudo().search([('id', 'child_of', medicine_roots.ids)]).ids
        ) if medicine_roots else set()
        if term:
            # Live typeahead search (DrugPicker's "أضف دواءً من المخزون"). The
            # full-catalog fetch this endpoint does when called with no filters
            # doesn't scale as the catalog grows (33k+ product templates and
            # counting) — a term search gets a real server-side query and a
            # small capped result instead of relying on a client-side filter
            # over the entire catalog.
            domain += ['|', '|',
                ('name', 'ilike', term),
                ('name_en', 'ilike', term),
                ('default_code', 'ilike', term),
            ]
            if medicines_only:
                domain += [('categ_id', 'in', list(medicine_categ_ids))]
        search_kwargs = {'limit': min(int(limit), 200) if limit else 50, 'order': 'name asc'} if term else {}
        records = request.env['product.template'].sudo().search(domain, **search_kwargs)
        all_uoms = request.env['uom.uom'].sudo().search([])

        # uom_options below used to call _compute_price/_has_common_reference
        # for every (product, uom) pair — 808 products × 44 uoms = ~35k calls
        # per request, which is what made this endpoint take 80s+. The price
        # ratio and compatibility for a given (base_uom, uom) pair don't
        # depend on the product itself, only on list_price (linear), so they
        # can be computed once per distinct base uom_id and reused.
        uom_ratio_cache = {}

        def uom_options_for(base_uom):
            if not base_uom:
                return []
            ratios = uom_ratio_cache.get(base_uom.id)
            if ratios is None:
                ratios = [(
                    uom.id, uom.name,
                    (uom.factor / base_uom.factor) if base_uom._has_common_reference(uom) else None,
                ) for uom in all_uoms]
                uom_ratio_cache[base_uom.id] = ratios
            return [{
                'id': uom_id,
                'name': uom_name,
                'price': rec_list_price * ratio if ratio is not None else rec_list_price,
            } for uom_id, uom_name, ratio in ratios]

        data = []
        for rec in records:
            rec_list_price = rec.list_price
            data.append({
                # ── identity ──────────────────────────────────────────────
                'id':                       rec.id,
                'name':                     rec.name,
                'name_en':                  rec.name_en or '',
                'generic_name':             rec.generic_name or '',
                'medicine_concentration':   rec.medicine_concentration or '',
                'primary_route':            rec.primary_route or '',
                'primary_route_label':      dict(rec._fields['primary_route'].selection).get(rec.primary_route, ''),
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
                'is_storable': rec.is_storable,
                'categ_id':                 rec.categ_id.id if rec.categ_id else None,
                'categ_name':               rec.categ_id.complete_name if rec.categ_id else None,
                'categ_name_ar':            rec.categ_id.name_ar if rec.categ_id else None,
                'is_medicines':             rec.categ_id.id in medicine_categ_ids if rec.categ_id else False,
                'active':                   rec.active,
                'sale_ok':                  rec.sale_ok,
                'purchase_ok':              rec.purchase_ok,
                'can_be_expensed':          getattr(rec, 'can_be_expensed', False),
                # ── uom ───────────────────────────────────────────────────
                'uom_id':                   rec.uom_id.id if rec.uom_id else None,
                'uom_name':                 rec.uom_id.name if rec.uom_id else None,
                'uom_largee':       rec.uom_largee.id   if rec.uom_largee   else None,
                'uom_large_name': rec.uom_largee.name if rec.uom_largee else '',
                'uom_mediumm': rec.uom_mediumm.id if rec.uom_mediumm else None,
                'uom_medium_name': rec.uom_mediumm.name if rec.uom_mediumm else '',
                # 'uom_po_id':                rec.uom_po_id.id if rec.uom_po_id else None,
                # 'uom_po_name':              rec.uom_po_id.name if rec.uom_po_id else None,
                # Packagings — base uom_id plus each additional packaging in uom_ids,
                # price-converted. This is the list dispense screens should build
                # the الوحدة dropdown from.
                'packaging_uom_ids': _packaging_options(rec),
                # Every unit of measure in the system, selectable for this product —
                # defaults to product.uom_id. Price is list_price converted through
                # uom.uom._compute_price against the product's base uom_id; units that
                # don't share a reference with uom_id (a different measurement family)
                # keep the unconverted list_price since their factors aren't comparable.
                # Only built when location_id is passed (pharmacy dispensing's
                # stock-filtered fetch, a few dozen products) — the only caller
                # that reads this field. Skipped for the unfiltered full-catalog
                # fetch, since a len(all_uoms)-sized list per product there was
                # blowing up json.dumps() with a MemoryError on larger catalogs.
                'uom_options': uom_options_for(rec.uom_id) if location_id else [],
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
                # ── manufacturer ──────────────────────────────────────────
                'manufacturer_id':          rec.manufacturer.id if rec.manufacturer else None,
                'manufacturer_name':        rec.manufacturer.name if rec.manufacturer else '',
                # ── image ─────────────────────────────────────────────────
                # image_128 (a small pre-resized thumbnail) is checked instead
                # of image_1920 — both are set/unset together, but fetching
                # the full-resolution blob 808 times just to test truthiness
                # was a big chunk of this endpoint's cost.
                'image_url':                '/web/image/product.template/%d/image_1920' % rec.id if rec.image_128 else '',
                # ── product variants ──────────────────────────────────────
                'product_variant_ids':      rec.product_variant_ids.ids,
                'product_variant_count':    rec.product_variant_count,
            })
        return http_response(data)

    @http.route('/api/v1/products/search', type='http', auth='user', methods=['GET'], csrf=False)
    def search_lite(self, term='', limit='50', offset='0', product_type='', categ_keyword='', **kw):
        """Lightweight product search for dropdowns — returns only the fields needed."""
        # Same reasoning as ProductController.get_all's location_id branch: a
        # product archived after it was stocked (e.g. discontinued) must stay
        # visible here too, since the pharmacy screens' full medicine catalog
        # is sourced from this endpoint and would otherwise silently drop it
        # even though it still has real quantity on hand.
        domain = [('active', 'in', [True, False])]
        if term:
            domain += ['|', '|', '|', '|',
                ('name', 'ilike', term),
                ('name_en', 'ilike', term),
                ('default_code', 'ilike', term),
                ('categ_id.name', 'ilike', term),
                ('categ_id.name_ar', 'ilike', term),
            ]
        if categ_keyword:
            # Matches on name, complete_name and name_ar, after Arabic
            # normalization so alef/ta-marbuta spelling differences (e.g.
            # "أشعة" vs "اشعة") don't hide a real match.
            domain += [('categ_id', 'in', _categ_ids_by_keyword(request.env, categ_keyword))]
        if product_type:
            domain.append(('type', '=', product_type))

        # getCachedProducts() (services/productsCache.js) intentionally asks
        # for a limit large enough to cache the *whole* catalog client-side —
        # capping this too low silently truncates it alphabetically, dropping
        # any product past that cutoff from every screen that reads the cache
        # (pharmacy dispensing screens, Nursing, Doctor, inpatient forms).
        # The real catalog has passed 33k product templates, so this cap
        # needs real headroom, not just a bump to the last time it ran out.
        limit_i  = min(int(limit),  50000)
        offset_i = max(int(offset), 0)

        total   = request.env['product.template'].sudo().search_count(domain)
        records = request.env['product.template'].sudo().search(
            domain, limit=limit_i, offset=offset_i, order='name asc'
        )
        # أدوية checkbox on product.category, expanded to subcategories — same
        # rule as ProductController.get_all, needed here too since the pharmacy
        # screens' medicine list is now sourced from this endpoint (no location
        # filter, so it can show every medicine regardless of which stock
        # location currently holds it).
        medicine_roots = request.env['product.category'].sudo().search([('is_medicines', '=', True)])
        medicine_categ_ids = set(
            request.env['product.category'].sudo().search([('id', 'child_of', medicine_roots.ids)]).ids
        ) if medicine_roots else set()
        items = [{
            'id':                rec.id,
            'name':              rec.name,
            'name_en':           rec.name_en or '',
            'default_code':      rec.default_code or '',
            'categ_id':          rec.categ_id.id if rec.categ_id else None,
            'categ_name':        rec.categ_id.complete_name if rec.categ_id else '',
            'categ_name_ar':     rec.categ_id.name_ar if rec.categ_id else '',
            'categ_parent_name': rec.categ_id.parent_id.name if rec.categ_id and rec.categ_id.parent_id else '',
            'is_medicines':      rec.categ_id.id in medicine_categ_ids if rec.categ_id else False,
            'uom_id':            rec.uom_id.id   if rec.uom_id else None,
            'uom_name':          rec.uom_id.name if rec.uom_id else '',
            'type':              rec.type,
            'qty_available':     rec.qty_available,
        } for rec in records]
        return http_response({'items': items, 'total': total, 'offset': offset_i, 'limit': limit_i})

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
            'is_storable' : rec.is_storable,
            'categ_id':                 rec.categ_id.id if rec.categ_id else None,
            'categ_name':               rec.categ_id.complete_name if rec.categ_id else None,
            'active':                   rec.active,
            'sale_ok':                  rec.sale_ok,
            'purchase_ok':              rec.purchase_ok,
            'can_be_expensed':          getattr(rec, 'can_be_expensed', False),
            'uom_id': rec.uom_id.id if rec.uom_id else None,
            'uom_name': rec.uom_id.name if rec.uom_id else None,
            'uom_largee': rec.uom_largee.id if rec.uom_largee else None,
            'uom_large_name': rec.uom_largee.name if rec.uom_largee else '',
            'uom_mediumm': rec.uom_mediumm.id if rec.uom_mediumm else None,
            'uom_medium_name': rec.uom_mediumm.name if rec.uom_mediumm else '',
            # 'uom_po_id':                rec.uom_po_id.id if rec.uom_po_id else None,
            # 'uom_po_name':              rec.uom_po_id.name if rec.uom_po_id else None,
            'packaging_uom_ids': _packaging_options(rec),
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
        data.update(_items_form_dict(rec))
        return http_response(data)


# ─────────────────────────────────────────────────────────────────────────────
#  stock.location
# ─────────────────────────────────────────────────────────────────────────────

class LocationController(http.Controller):

    @http.route('/api/v1/stock/locations', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['stock.location'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            try:
                data.append({
                    'id':           rec.id,
                    'name':         rec.name,
                    'complete_name': rec.complete_name,
                    'usage':        rec.usage,
                    'location_id':  rec.location_id.id if rec.location_id else None,
                    'parent_name':  rec.location_id.complete_name if rec.location_id else None,
                    'active':       rec.active,
                    'company_id':   rec.company_id.id if rec.company_id else None,
                    'company_name': rec.company_id.name if rec.company_id else None,
                    'warehouse_id': rec.warehouse_id.id if rec.warehouse_id else None,
                    'warehouse_name': rec.warehouse_id.name if rec.warehouse_id else None,
                })
            except Exception:
                continue
        return http_response(data)

    @http.route('/api/v1/stock/locations/my', type='http', auth='user', methods=['GET'], csrf=False)
    def get_my(self, **kw):
        """المواقع المخصصة للمستخدم الحالي (hr.employee.location_ids) — تُستخدم
        لتقييد من يمكنه إنشاء/إرسال كميات/استلام طلبات صرف واستلام الأقسام،
        بدلاً من قصر التخصيص على مخزن كامل فقط."""
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        locations = employee.location_ids if employee else request.env['stock.location']
        return http_response([{
            'id':             loc.id,
            'name':           loc.name,
            'complete_name':  loc.complete_name,
            'warehouse_id':   loc.warehouse_id.id if loc.warehouse_id else None,
            'warehouse_name': loc.warehouse_id.name if loc.warehouse_id else None,
        } for loc in locations])

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
                'purchase_id':              getattr(rec, 'purchase_id', False) and rec.purchase_id.id or None,
                'purchase_name':            getattr(rec, 'purchase_id', False) and rec.purchase_id.name or None,
                'sale_id':                  getattr(rec, 'sale_id', False) and rec.sale_id.id or None,
                'sale_name':                getattr(rec, 'sale_id', False) and rec.sale_id.name or None,
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
                'is_locked':                getattr(rec, 'is_locked', False),
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
                'reference':                getattr(move, 'reference', '') or '',
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
                'q_sant':                   getattr(move, 'q_sant', 0.0),
                'qty_done':                 sum(ml.qty_done for ml in move.move_line_ids) if move.move_line_ids else move.quantity,
                'availability':             getattr(move, 'availability', 0.0),
                # ── uom ───────────────────────────────────────────────────
                'product_uom':              move.product_uom.id   if move.product_uom else None,
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
                'price_unit':               getattr(move, 'price_unit', 0.0),
                'value':                    getattr(move, 'value', 0.0),
                # ── links ─────────────────────────────────────────────────
                'purchase_line_id':         getattr(move, 'purchase_line_id', False) and move.purchase_line_id.id or None,
                'sale_line_id':             getattr(move, 'sale_line_id', False) and move.sale_line_id.id or None,
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
            'purchase_id':              getattr(rec, 'purchase_id', False) and rec.purchase_id.id or None,
            'purchase_name':            getattr(rec, 'purchase_id', False) and rec.purchase_id.name or None,
            'sale_id':                  getattr(rec, 'sale_id', False) and rec.sale_id.id or None,
            'sale_name':                getattr(rec, 'sale_id', False) and rec.sale_id.name or None,
            'backorder_id':             rec.backorder_id.id if rec.backorder_id else None,
            'backorder_name':           rec.backorder_id.name if rec.backorder_id else None,
            'user_id':                  rec.user_id.id if rec.user_id else None,
            'user_name':                rec.user_id.name if rec.user_id else None,
            'owner_id':                 rec.owner_id.id if rec.owner_id else None,
            'owner_name':               rec.owner_id.name if rec.owner_id else None,
            'company_id':               rec.company_id.id if rec.company_id else None,
            'company_name':             rec.company_id.name if rec.company_id else None,
            'is_locked':                getattr(rec, 'is_locked', False),
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
                'reference':                getattr(rec, 'reference', '') or '',
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
                'availability':             getattr(rec, 'availability', 0.0),
                # ── uom ───────────────────────────────────────────────────
                'product_uom':              rec.product_uom.id   if rec.product_uom else None,
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
                'price_unit':               getattr(rec, 'price_unit', 0.0),
                'value':                    getattr(rec, 'value', 0.0),
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
                'note':                 rec.note or '',
                # ── partner ───────────────────────────────────────────────
                'partner_id':           rec.partner_id.id if rec.partner_id else None,
                'partner_name':         rec.partner_id.name if rec.partner_id else None,
                'dest_address_id':      rec.dest_address_id.id if rec.dest_address_id else None,
                'dest_address_name':    rec.dest_address_id.name if rec.dest_address_id else None,
                # ── deliver to ───────────────────────────────────────────
                'picking_type_id':      rec.picking_type_id.id if rec.picking_type_id else None,
                'picking_type_name':    rec.picking_type_id.name if rec.picking_type_id else None,
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
                # ── attachments ───────────────────────────────────────────
                'request_documents_count':    len(rec.request_document_ids),
                'inspection_documents_count': len(rec.inspection_document_ids),
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
                'product_uom':              line.product_uom_id.id   if line.product_uom_id else None,
                'product_uom_name':         line.product_uom_id.name if line.product_uom_id else None,
                # ── pricing ───────────────────────────────────────────────
                'price_unit':               line.price_unit,
                'discount':                 line.discount,
                'taxes_id':                 line.tax_ids.ids,
                'tax_names':                ', '.join(line.tax_ids.mapped('name')),
                'tax_percent':              line.tax_ids[:1].amount if line.tax_ids else None,
                'price_subtotal':           line.price_subtotal,
                'price_total':              line.price_total,
                'price_tax':                line.price_tax,
                # ── dates ─────────────────────────────────────────────────
                'date_planned':             str(line.date_planned) if line.date_planned else None,
                # ── links ─────────────────────────────────────────────────
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
            'note':                 rec.note or '',
            'partner_id':           rec.partner_id.id if rec.partner_id else None,
            'partner_name':         rec.partner_id.name if rec.partner_id else None,
            'dest_address_id':      rec.dest_address_id.id if rec.dest_address_id else None,
            'dest_address_name':    rec.dest_address_id.name if rec.dest_address_id else None,
            'picking_type_id':      rec.picking_type_id.id if rec.picking_type_id else None,
            'picking_type_name':    rec.picking_type_id.name if rec.picking_type_id else None,
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
            # ── attachments ───────────────────────────────────────────────
            'request_documents':    _cr_attachment_list(rec.request_document_ids),
            'inspection_documents': _cr_attachment_list(rec.inspection_document_ids),
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
            # ── optional simple fields ────────────────────────────────────
            for field in ['default_code', 'barcode', 'type',
                          'sale_ok', 'purchase_ok',
                          'description', 'description_sale',
                          'description_purchase', 'tracking',
                          'description_picking', 'description_pickingout',
                          'description_pickingin']:
                if field in body:
                    vals[field] = body[field]

            # ── price fields (cast to float) ──────────────────────────────
            # standard_price = سعر الشراء الموحد (Cost)
            # list_price     = سعر الشراء الجبري (Sales Price)
            for price_field in ('standard_price', 'list_price'):
                if price_field in body and body[price_field] is not None and body[price_field] != '':
                    try:
                        vals[price_field] = float(body[price_field])
                    except (TypeError, ValueError):
                        return http_response(
                            {'error': f'{price_field} must be a number'}, 400
                        )
            if 'type' in body:
             if body['type'] == 'product':
                vals['type'] = 'consu'
                vals['is_storable'] = True
             elif body['type'] == 'consu':
                  vals['type'] = 'consu'
                  vals['is_storable'] = False
             elif body['type'] == 'service':
                 vals['type'] = 'service'
                 vals['is_storable'] = False
                        # ── image (base64 string) ─────────────────────────────────────
            if body.get('image_1920'):
             vals['image_1920'] = body['image_1920']

            # ── شاشة الأصناف والأدوية fields (see helper near top of file) ──
            _apply_items_form_vals(body, vals)

            # ── many2one fields – validate existence ──────────────────────
            m2o_fields = {
                'categ_id':   'product.category',
                'uom_id':     'uom.uom',
                'uom_po_id':  'uom.uom',
                'uom_large': 'uom.uom',
                'uom_medium': 'uom.uom',
            }
            for field, model in m2o_fields.items():
                if body.get(field):
                    related = request.env[model].sudo().browse(int(body[field]))
                    if not related.exists():
                        return http_response({'error': f'{field} not found'}, 400)
                    vals[field] = related.id

            rec = request.env['product.template'].sudo().create(vals)

            response = {
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
            }
            response.update(_items_form_dict(rec))
            return http_response(response, 201)

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

                # partner optional — attach if provided
                if line.get('partner_id'):
                    partner = request.env['res.partner'].sudo().browse(int(line['partner_id']))
                    if partner.exists():
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

            for field in ['name', 'default_code', 'barcode', 'type',
                          'sale_ok', 'purchase_ok', 'active',
                          'description', 'description_sale', 'description_purchase',
                          'tracking', 'description_picking', 'description_pickingout',
                          'description_pickingin',
                          'uom_large', 'uom_medium']:
                if field in body:
                    vals[field] = body[field]

            # ── price fields (cast to float) ──────────────────────────────
            # standard_price = سعر الشراء الموحد (Cost)
            # list_price     = سعر الشراء الجبري (Sales Price)
            for price_field in ('standard_price', 'list_price'):
                if price_field in body:
                    if body[price_field] is None or body[price_field] == '':
                        continue
                    try:
                        vals[price_field] = float(body[price_field])
                    except (TypeError, ValueError):
                        return http_response(
                            {'error': f'{price_field} must be a number'}, 400
                        )
            if 'type' in body:
                if body['type'] == 'product':
                   vals['type'] = 'consu'
                   vals['is_storable'] = True
                elif body['type'] == 'consu':
                    vals['type'] = 'consu'
                    vals['is_storable'] = False
                elif body['type'] == 'service':
                     vals['type'] = 'service'
                     vals['is_storable'] = False
                        # ── image (base64 string, or null to clear) ───────────────────
            if 'image_1920' in body:
             vals['image_1920'] = body['image_1920'] or False

            # ── شاشة الأصناف والأدوية fields (see helper near top of file) ──
            _apply_items_form_vals(body, vals)

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

            response = {
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
            }
            response.update(_items_form_dict(rec))
            return http_response(response)

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
                'categ_id':             rec.product_id.categ_id.id if rec.product_id and rec.product_id.categ_id else None,
                'categ_name':           rec.product_id.categ_id.name if rec.product_id and rec.product_id.categ_id else None,
                'product_uom_id':       rec.product_uom_id.id if rec.product_uom_id else None,
                'product_uom_name':     rec.product_uom_id.name if rec.product_uom_id else None,
                'location_id':          rec.location_id.id if rec.location_id else None,
                'location_name':        rec.location_id.complete_name if rec.location_id else None,
                'lot_id':               rec.lot_id.id if rec.lot_id else None,
                'lot_name':             rec.lot_id.name if rec.lot_id else None,
                # expiration_date only exists on stock.lot when product_expiry is
                # installed — getattr avoids an AttributeError on installs without it.
                'expiration_date':      str(getattr(rec.lot_id, 'expiration_date', False).date()) if getattr(rec.lot_id, 'expiration_date', False) else None,
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

    @http.route('/api/v1/stock/warehouses/my', type='http', auth='user', methods=['GET'], csrf=False)
    def get_my(self, **kw):
        """Warehouses assigned to the current user's hr.employee record
        (hr.employee.warehouse_ids) - scopes which sub-warehouse destination
        locations they're allowed to receive transfers into on شاشة نقل
        للمخازن الفرعية / طلبات صرف واستلام الأقسام."""
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        warehouses = employee.warehouse_ids if employee else request.env['stock.warehouse']
        return http_response([{
            'id':             wh.id,
            'name':           wh.name,
            'code':           wh.code,
            'lot_stock_id':   wh.lot_stock_id.id if wh.lot_stock_id else None,
            'lot_stock_name': wh.lot_stock_id.complete_name if wh.lot_stock_id else None,
        } for wh in warehouses])


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

            # طلبات صرف واستلام الأقسام: فقط الموظف المخوّل بموقع الوجهة هو من
            # يمكنه إنشاء طلب موجّه إليه — نفس منطق الاستلام لاحقاً، لكن على
            # لحظة الإنشاء. مقيّد بـ 'internal' فقط، فلا يمس شاشات الصيدلية.
            if picking_type.code == 'internal':
                employee = request.env['hr.employee'].sudo().search(
                    [('user_id', '=', request.env.user.id)], limit=1
                )
                if not _location_covered(location_dst, employee):
                    return http_response({'error': 'هذا الموقع غير مخصص لك — لا يمكنك إنشاء طلب موجّه إليه'}, 403)

            vals = {
                'picking_type_id':  picking_type.id,
                'location_id':      location_src.id,
                'location_dest_id': location_dst.id,
                # المرسل: the person creating the transfer request — defaults
                # to whoever is logged in, so طلبات صرف واستلام الأقسام can
                # show "المرسل" without the client having to pass it explicitly.
                'user_id':          request.env.user.id,
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
                # The React product pickers (searchProductsFast) return product.template
                # ids, but a stock.move needs a product.product variant — resolve the
                # template's variant first, falling back to a direct browse in case this
                # is already a product.product id (e.g. re-sent from a loaded picking).
                raw_id = int(move['product_id'])
                product = request.env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', raw_id)], limit=1
                )
                if not product:
                    product = request.env['product.product'].sudo().browse(raw_id)
                if not product.exists():
                    return http_response({'error': f'moves[{i}]: product_id not found'}, 400)

                qty = float(move.get('quantity', move.get('product_uom_qty', 1)))
                move_uom_id = move.get('product_uom') or product.uom_id.id
                move_vals_list.append((0, 0, {
                    'product_id':       product.id,
                    'product_uom_qty':  qty,
                    'product_uom':      move_uom_id,
                    'location_id':      location_src.id,
                    'location_dest_id': location_dst.id,
                }))

            vals['move_ids'] = move_vals_list
            rec = request.env['stock.picking'].sudo().create(vals)

            # إشعار المستخدمين المخوّلين بموقع المصدر — هم من يجهّز/يرسل
            # الطلب تالياً، بخلاف موقع الوجهة الذي غالباً هو من أنشأ الطلب
            # أصلاً ولا حاجة لإخباره بإجرائه هو. فقط لتحويلات الأقسام
            # الداخلية (طلبات صرف واستلام الأقسام)، وليس لعمليات الصيدلية.
            if picking_type.code == 'internal':
                try:
                    candidates = request.env['hr.employee'].sudo().search([('location_ids', '!=', False)])
                    recipients = candidates.filtered(
                        lambda e: _location_covered(location_src, e)
                    ).mapped('user_id')
                    for u in recipients:
                        request.env['saycare.notification'].sudo().create({
                            'user_id': u.id,
                            'title':   f'طلب جديد يحتاج تجهيز: {rec.name}',
                            'body':    f'من {location_src.complete_name} إلى {location_dst.complete_name}',
                            'url':     f'/unit/sub-storage-transfer?picking={rec.id}',
                        })
                except Exception:
                    pass

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
                'user_id':            rec.user_id.id if rec.user_id else None,
                'user_name':          rec.user_id.name if rec.user_id else None,
            }, 201)

        except Exception as e:
            return http_response({'error': str(e)}, 500)


class PickingConfirmController(http.Controller):

    @http.route('/api/v1/stock/pickings/<int:rec_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm_picking(self, rec_id, **kw):
        try:
            rec = request.env['stock.picking'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state not in ('draft', 'waiting', 'confirmed'):
                return http_response({'error': f'cannot confirm in state: {rec.state}'}, 400)
            rec.action_confirm()
            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/stock/pickings/<int:rec_id>/moves/<int:move_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_move(self, rec_id, move_id, **kw):
        try:
            rec = request.env['stock.picking'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'picking not found'}, 404)
            move = request.env['stock.move'].sudo().browse(move_id)
            if not move.exists() or move.picking_id.id != rec_id:
                return http_response({'error': 'move not found in this picking'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            if 'q_sant' in body:
                move.q_sant = float(body['q_sant'])
            if 'qty_done' in body:
                move.quantity = float(body['qty_done'])
            qty_done = sum(ml.qty_done for ml in move.move_line_ids) if move.move_line_ids else move.quantity
            return http_response({'id': move.id, 'q_sant': move.q_sant, 'qty_done': qty_done})
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/stock/pickings/<int:rec_id>/save-quantities', type='http', auth='user', methods=['POST'], csrf=False)
    def save_quantities(self, rec_id, **kw):
        """Save q_sant + qty_done for each move and mark picking as quantities_confirmed."""
        try:
            rec = request.env['stock.picking'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state == 'done':
                return http_response({'error': 'picking is already done'}, 400)
            if rec.state == 'cancel':
                return http_response({'error': 'picking is cancelled'}, 400)

            # طلبات صرف واستلام الأقسام: تحديد وإرسال الكميات (المرحلة التي
            # يجهّز فيها المخزن الطلب) مقصورة على موظفي مخزن المصدر — عكس
            # الاستلام الذي يخص مخزن الوجهة. مقيّد بـ 'internal' فقط.
            if rec.picking_type_id.code == 'internal':
                employee = request.env['hr.employee'].sudo().search(
                    [('user_id', '=', request.env.user.id)], limit=1
                )
                if not _location_covered(rec.location_id, employee):
                    return http_response({'error': 'هذا الموقع غير مخصص لك — لا يمكنك تحديد أو إرسال كميات هذا الطلب'}, 403)

            body = json.loads(request.httprequest.data or '{}')
            moves_data = body.get('moves', [])

            for entry in moves_data:
                move_id = entry.get('move_id')
                if not move_id:
                    continue
                move = request.env['stock.move'].sudo().browse(int(move_id))
                if not move.exists() or move.picking_id.id != rec_id:
                    continue
                if 'q_sant' in entry:
                    move.q_sant = float(entry['q_sant'])
                if 'qty_done' in entry:
                    move.quantity = float(entry['qty_done'])

            rec.write({'state': 'quantities_confirmed'})

            # إشعار المستخدمين المخوّلين بمخزن الوجهة — الطلب أصبح جاهزاً
            # لتأكيد الاستلام. فقط لتحويلات الأقسام الداخلية.
            if rec.picking_type_id.code == 'internal':
                try:
                    candidates = request.env['hr.employee'].sudo().search([('location_ids', '!=', False)])
                    recipients = candidates.filtered(
                        lambda e: _location_covered(rec.location_dest_id, e)
                    ).mapped('user_id')
                    for u in recipients:
                        request.env['saycare.notification'].sudo().create({
                            'user_id': u.id,
                            'title':   f'الطلب جاهز للاستلام: {rec.name}',
                            'body':    f'من {rec.location_id.complete_name} إلى {rec.location_dest_id.complete_name}',
                            'url':     f'/unit/sub-storage-transfer?picking={rec.id}',
                        })
                except Exception:
                    pass

            moves_out = []
            for move in rec.move_ids:
                moves_out.append({
                    'id':              move.id,
                    'q_sant':          getattr(move, 'q_sant', 0.0),
                    'qty_done':        move.quantity,
                    'product_uom_qty': move.product_uom_qty,
                })

            return http_response({
                'id':    rec.id,
                'name':  rec.name,
                'state': rec.state,
                'moves': moves_out,
            })
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

            # طلبات صرف واستلام الأقسام (SubStorageTransferPage.jsx) - only the
            # employee(s) assigned to the destination location may confirm
            # receipt. Scoped strictly to 'internal' transfers so unrelated
            # flows (purchase receiving, pharmacy dispensing via 'outgoing')
            # are never affected. An employee with no location_ids configured
            # yet is denied, not let through — see _location_covered.
            if rec.picking_type_id.code == 'internal':
                employee = request.env['hr.employee'].sudo().search(
                    [('user_id', '=', request.env.user.id)], limit=1
                )
                if not _location_covered(rec.location_dest_id, employee):
                    return http_response({'error': 'هذا الموقع غير مخصص لك — لا يمكنك تأكيد الاستلام هنا'}, 403)

            # Confirm first if still in draft
            if rec.state in ('draft', 'waiting', 'confirmed'):
                rec.action_confirm()
                rec.action_assign()

            body = json.loads(request.httprequest.data or '{}')

            # Set done quantities to match demand for any move that has none
            if body.get('immediate_transfer', True):
                for move in rec.move_ids:
                    if move.quantity == 0:
                        move.quantity = move.product_uom_qty

            # Auto-generate lot/serial numbers for tracked products that have none.
            # This prevents the "You need to supply a Lot/Serial number" UserError.
            # Lot name includes picking_id + move_id + line_index to guarantee uniqueness.
            ts = int(time.time())

            def _unique_lot_name(prefix, product, move, idx=0):
                """Return a lot name guaranteed not to exist yet for this product."""
                base = f'{prefix}-{product.default_code or product.id}-{rec.id}-{move.id}-{idx}'
                while request.env['stock.lot'].sudo().search_count([
                    ('name', '=', base), ('product_id', '=', product.id),
                    ('company_id', '=', move.company_id.id)
                ]):
                    base = f'{base}-{ts}'
                return base

            for move in rec.move_ids:
                tracking = move.product_id.tracking
                if tracking == 'none':
                    continue
                for li, ml in enumerate(move.move_line_ids):
                    if ml.lot_id:
                        continue
                    if tracking == 'serial':
                        # Serial: one lot per unit — split move_line if qty > 1
                        qty = int(ml.quantity) or 1
                        if qty <= 1:
                            lot = request.env['stock.lot'].sudo().create({
                                'name':       _unique_lot_name('SN', move.product_id, move, li),
                                'product_id': move.product_id.id,
                                'company_id': move.company_id.id,
                            })
                            ml.sudo().write({'lot_id': lot.id})
                        else:
                            first = True
                            for i in range(qty):
                                lot = request.env['stock.lot'].sudo().create({
                                    'name':       _unique_lot_name('SN', move.product_id, move, li * 1000 + i),
                                    'product_id': move.product_id.id,
                                    'company_id': move.company_id.id,
                                })
                                if first:
                                    ml.sudo().write({'lot_id': lot.id, 'quantity': 1.0})
                                    first = False
                                else:
                                    request.env['stock.move.line'].sudo().create({
                                        'move_id':          move.id,
                                        'product_id':       move.product_id.id,
                                        'product_uom_id':   move.product_uom.id,
                                        'location_id':      ml.location_id.id,
                                        'location_dest_id': ml.location_dest_id.id,
                                        'lot_id':           lot.id,
                                        'quantity':         1.0,
                                        'picking_id':       rec.id,
                                        'company_id':       move.company_id.id,
                                    })
                    else:
                        # Lot tracking: one lot per move_line
                        lot = request.env['stock.lot'].sudo().create({
                            'name':       _unique_lot_name('LOT', move.product_id, move, li),
                            'product_id': move.product_id.id,
                            'company_id': move.company_id.id,
                        })
                        ml.sudo().write({'lot_id': lot.id})

            # skip_backorder / skip_immediate prevent wizard popups in Odoo 17+
            res = rec.with_context(
                skip_backorder=True,
                skip_sms=True,
                skip_immediate=True,
                picking_ids_not_to_backorder=rec.ids,
            ).button_validate()

            # If Odoo still returned a wizard action, force-validate directly
            if isinstance(res, dict) and res.get('res_model'):
                rec._action_done()

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
#  res.partner  — vendors only
# ─────────────────────────────────────────────────────────────────────────────

class VendorController(http.Controller):

    _WRITABLE = [
        'name', 'email', 'phone', 'website',
        'street', 'street2', 'city', 'zip', 'vat', 'comment', 'ref', 'is_vendor',
    ]

    def _vendor_dict(self, rec):
        po_count = 0
        try:
            po_count = rec.purchase_order_count
        except Exception:
            pass
        return {
            'id':            rec.id,
            'name':          rec.name,
            'ref':           rec.ref or '',
            'email':         rec.email or '',
            'phone':         rec.phone or '',
            'mobile':        getattr(rec, 'mobile', None) or '',
            'website':       rec.website or '',
            'street':        rec.street or '',
            'street2':       rec.street2 or '',
            'city':          rec.city or '',
            'zip':           rec.zip or '',
            'state_name':    rec.state_id.name if rec.state_id else '',
            'country_id':    rec.country_id.id if rec.country_id else None,
            'country_name':  rec.country_id.name if rec.country_id else None,
            'vat':           rec.vat or '',
            'lang':          rec.lang or '',
            'comment':       rec.comment or '',
            'supplier_rank': rec.supplier_rank,
            'is_company':    rec.is_company,
            'company_type':  rec.company_type,
            'parent_id':     rec.parent_id.id if rec.parent_id else None,
            'parent_name':   rec.parent_id.name if rec.parent_id else None,
            'image_url':     '/web/image/res.partner/%d/image_1920' % rec.id if rec.image_1920 else '',
            'purchase_order_count': po_count,
            'is_vendor': bool(getattr(rec, 'is_vendor', False)),
        }
    @http.route('/api/v1/partners/vendors', type='http', auth='user', methods=['GET'], csrf=False)
    def get_vendors(self, **kw):
        # Base filter: active partners only
        domain = [('active', '=', True)]

        # If ?is_vendor=true is passed, use the custom vendor flag.
        # Otherwise preserve the existing Odoo supplier_rank behavior.
        only_vendors = str(kw.get('is_vendor', '')).lower() in ('1', 'true', 'yes')
        if only_vendors:
            domain.append(('is_vendor', '=', True))
        else:
            domain.append(('supplier_rank', '>', 0))

        search = (kw.get('q') or '').strip()

        # Keep the endpoint backward-compatible for callers that request the
        # normal vendor list without q. Search callers that explicitly send q
        # must type at least two characters.
        if 'q' in kw and len(search) < 2:
            return http_response([])

        if search:
            domain.extend([
                '|',
                ('name', 'ilike', search),
                ('ref', 'ilike', search),
            ])

        try:
            limit = int(kw.get('limit') or 0)
        except (TypeError, ValueError):
            limit = 0
        limit = max(0, min(limit, 50))

        records = request.env['res.partner'].sudo().search(
            domain,
            order='name asc',
            limit=limit,
        )

        data = []
        for rec in records:
            try:
                data.append(self._vendor_dict(rec))
            except Exception:
                continue
        return http_response(data)



    @http.route('/api/v1/partners/vendors/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_vendor(self, rec_id, **kw):
        rec = request.env['res.partner'].sudo().browse(rec_id)
        if not rec.exists():
            return http_response({'error': 'not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
            vals = {f: body[f] for f in self._WRITABLE if f in body}
            if 'is_company' in body:
                vals['is_company'] = bool(body['is_company'])
            if 'is_vendor' in vals:
                vals['is_vendor'] = bool(vals['is_vendor'])
            if vals:
                rec.write(vals)
            return http_response(self._vendor_dict(rec))
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/partners/vendors', type='http', auth='user', methods=['POST'], csrf=False)
    def create_vendor(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
            if not body.get('name'):
                return http_response({'error': 'name is required'}, 400)
            vals = {
                'supplier_rank': 1,
                'is_company': bool(body.get('is_company', True)),
                'is_vendor': bool(body.get('is_vendor', False)),
            }
            vals.update({f: body[f] for f in self._WRITABLE if body.get(f)})
            rec = request.env['res.partner'].sudo().create(vals)
            return http_response(self._vendor_dict(rec))
        except Exception as e:
            return http_response({'error': str(e)}, 500)


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

            for field in ('origin', 'partner_ref', 'date_order', 'date_planned'):
                if body.get(field):
                    vals[field] = body[field]

            if body.get('notes'):
                vals['note'] = body['notes']

            if body.get('currency_id'):
                currency = request.env['res.currency'].sudo().browse(int(body['currency_id']))
                if currency.exists():
                    vals['currency_id'] = currency.id

            if body.get('picking_type_id'):
                picking_type = request.env['stock.picking.type'].sudo().browse(int(body['picking_type_id']))
                if picking_type.exists():
                    vals['picking_type_id'] = picking_type.id

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

                line_vals = {
                    'product_id':    product.id,
                    'name':          product.display_name,
                    'product_qty':   qty,
                    'price_unit':    price,
                    'product_uom_id': uom_id,
                    'discount':      float(line.get('discount') or 0),
                    'date_planned':  line.get('date_planned') or body.get('date_planned') or now_str,
                }
                if line.get('tax_percent') not in (None, ''):
                    pct = float(line['tax_percent'])
                    tax = request.env['account.tax'].sudo().search([
                        ('type_tax_use', '=', 'purchase'),
                        ('amount_type', '=', 'percent'),
                        ('amount', '=', pct),
                        ('company_id', '=', request.env.company.id),
                    ], limit=1)
                    if not tax:
                        tax = request.env['account.tax'].sudo().create({
                            'name':          f'ضريبة شراء {pct:g}%',
                            'amount':        pct,
                            'amount_type':   'percent',
                            'type_tax_use':  'purchase',
                            'company_id':    request.env.company.id,
                        })
                    line_vals['tax_ids'] = [(6, 0, tax.ids)]
                line_vals_list.append((0, 0, line_vals))

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


_PO_ATTACHMENT_FIELDS = {
    'request':    'request_document_ids',
    'inspection': 'inspection_document_ids',
}


class PurchaseOrderAttachmentController(http.Controller):

    @http.route('/api/v1/purchase/orders/<int:rec_id>/attachments', type='http', auth='user', methods=['POST'], csrf=False)
    def add_attachment(self, rec_id, **kw):
        try:
            rec = request.env['purchase.order'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            field = _PO_ATTACHMENT_FIELDS.get(body.get('field'))
            if not field:
                return http_response({'error': "field must be 'request' or 'inspection'"}, 400)
            data = body.get('data')
            if not data:
                return http_response({'error': 'data (base64) is required'}, 400)
            attachment = request.env['ir.attachment'].sudo().create({
                'name':      body.get('name') or 'attachment',
                'datas':     data,
                'mimetype':  body.get('mimetype') or False,
                'res_model': 'purchase.order',
                'res_id':    rec.id,
            })
            rec[field] = [(4, attachment.id)]
            return http_response(_cr_attachment_list(rec[field]), 201)
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/orders/<int:rec_id>/attachments/<int:attachment_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def remove_attachment(self, rec_id, attachment_id, **kw):
        try:
            rec = request.env['purchase.order'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            field = _PO_ATTACHMENT_FIELDS.get(kw.get('field'))
            if not field:
                return http_response({'error': "field must be 'request' or 'inspection'"}, 400)
            rec[field] = [(3, attachment_id)]
            return http_response(_cr_attachment_list(rec[field]))
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
    def get_dashboard(self, date_from='', date_to='', **kw):
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
        try:
            expiring_count = env['stock.lot'].sudo().search_count([
                ('expiration_date', '!=', False),
                ('expiration_date', '>=', str(today)),
                ('expiration_date', '<=', str(in_30)),
            ])
        except Exception:
            expiring_count = 0

        if date_from:
            try:
                range_start = odoo_fields.Datetime.to_string(
                    datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                )
                range_end = odoo_fields.Datetime.to_string(
                    datetime.strptime(date_to or date_from, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                )
            except ValueError:
                range_start = odoo_fields.Datetime.to_string(
                    odoo_fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                )
                range_end = None
        else:
            range_start = odoo_fields.Datetime.to_string(
                odoo_fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            )
            range_end = None

        move_domain = [('state', '=', 'done'), ('date_done', '>=', range_start)]
        if range_end:
            move_domain.append(('date_done', '<=', range_end))
        todays_movements = env['stock.picking'].sudo().search_count(move_domain)

        try:
            pending_requisitions = env['employee.purchase.requisition'].sudo().search_count([
                ('state', 'in', ['new', 'waiting_department_approval', 'waiting_head_approval']),
            ])
        except Exception:
            pending_requisitions = 0

        try:
            pending_pos = env['purchase.order'].sudo().search_count([
                ('state', 'in', ['draft', 'sent']),
            ])
        except Exception:
            pending_pos = 0

        return http_response({
            'total_products':       total_products,
            'total_qty_onhand':     total_qty,
            'below_safety_count':   below_safety_count,
            'expiring_soon_count':  expiring_count,
            'todays_movements':     todays_movements,
            'pending_requisitions': pending_requisitions,
            'pending_pos':          pending_pos,
        })

    @http.route('/api/v1/inventory/alerts', type='http', auth='user', methods=['GET'], csrf=False)
    def get_alerts(self, date_from='', date_to='', **kw):
        env = request.env
        today  = date.today()
        in_30  = today + timedelta(days=30)

        if date_from:
            try:
                moves_start = odoo_fields.Datetime.to_string(
                    datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                )
                moves_end = odoo_fields.Datetime.to_string(
                    datetime.strptime(date_to or date_from, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                )
            except ValueError:
                moves_start = odoo_fields.Datetime.to_string(
                    odoo_fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                )
                moves_end = None
        else:
            moves_start = odoo_fields.Datetime.to_string(
                odoo_fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            )
            moves_end = None

        # ── low-stock: quants with qty <= 0 in internal locations ────────────
        quants = env['stock.quant'].sudo().search([('location_id.usage', '=', 'internal')])
        low_stock = []
        seen = set()
        for q in quants:
            try:
                if q.quantity <= 0 and q.product_id.id not in seen:
                    seen.add(q.product_id.id)
                    low_stock.append({
                        'id':    q.product_id.id,
                        'name':  q.product_id.name,
                        'qty':   q.quantity,
                        'unit':  q.product_uom_id.name if q.product_uom_id else 'وحدة',
                        'categ': q.product_id.categ_id.name if q.product_id.categ_id else '',
                    })
            except Exception:
                continue

        # ── expiring soon: lots expiring in next 30 days ─────────────────────
        try:
            lots = env['stock.lot'].sudo().search([
                ('expiration_date', '!=', False),
                ('expiration_date', '>=', str(today)),
                ('expiration_date', '<=', str(in_30)),
            ], limit=20, order='expiration_date asc')
        except Exception:
            lots = env['stock.lot'].sudo().browse([])
        expiring = []
        for lot in lots:
            try:
                qty = sum(lot.quant_ids.filtered(
                    lambda q: q.location_id.usage == 'internal'
                ).mapped('quantity'))
                expiring.append({
                    'id':           lot.id,
                    'product_name': lot.product_id.name if lot.product_id else '',
                    'lot':          lot.name,
                    'expiry':       str(lot.expiration_date)[:10] if lot.expiration_date else '',
                    'qty':          qty,
                })
            except Exception:
                continue

        # ── recent moves: done pickings in the requested date range ──────────
        pick_domain = [('state', '=', 'done'), ('date_done', '>=', moves_start)]
        if moves_end:
            pick_domain.append(('date_done', '<=', moves_end))
        pickings = env['stock.picking'].sudo().search(
            pick_domain, limit=20, order='date_done desc'
        )
        recent = []
        for p in pickings:
            try:
                recent.append({
                    'id':      p.id,
                    'name':    p.name,
                    'partner': p.partner_id.name if p.partner_id else '',
                    'type':    p.picking_type_id.name if p.picking_type_id else '',
                    'state':   p.state,
                    'date':    str(p.date_done)[:16] if p.date_done else '',
                })
            except Exception:
                continue

        return http_response({
            'low_stock':    low_stock[:20],
            'expiring':     expiring,
            'recent_moves': recent,
        })

    @http.route('/api/v1/inventory/stagnant-report', type='http', auth='user', methods=['GET'], csrf=False)
    def get_stagnant_report(self, days='90', **kw):
        """تقرير الرواكد: أصناف بدون أي حركة مخزنية خلال آخر N يوم (افتراضياً 90 يوم / 3 أشهر)،
        بالإضافة إلى الأصناف منتهية الصلاحية والموجودة بالمخزون فعلياً."""
        env = request.env
        try:
            days_n = int(days)
        except (TypeError, ValueError):
            days_n = 90
        today = date.today()
        cutoff = today - timedelta(days=days_n)

        # ── on-hand quants grouped by product ────────────────────────────────
        quants = env['stock.quant'].sudo().search([
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
        ])
        by_product = {}
        for q in quants:
            pid = q.product_id.id
            entry = by_product.setdefault(pid, {'product': q.product_id, 'qty': 0.0, 'uom': ''})
            entry['qty'] += q.quantity
            if not entry['uom'] and q.product_uom_id:
                entry['uom'] = q.product_uom_id.name

        last_move_by_product = {}
        if by_product:
            groups = env['stock.move'].sudo().read_group(
                [('product_id', 'in', list(by_product.keys())), ('state', '=', 'done')],
                ['date:max'], ['product_id'],
            )
            for g in groups:
                pid = g['product_id'][0] if g.get('product_id') else None
                if pid:
                    last_move_by_product[pid] = g.get('date')

        stagnant = []
        for pid, info in by_product.items():
            last_dt = last_move_by_product.get(pid)
            last_date = last_dt.date() if hasattr(last_dt, 'date') else last_dt
            if last_date and last_date > cutoff:
                continue
            days_idle = (today - last_date).days if last_date else None
            stagnant.append({
                'product_id':           pid,
                'product_name':         info['product'].name,
                'product_default_code': info['product'].default_code or '',
                'categ_name':           info['product'].categ_id.name if info['product'].categ_id else '',
                'qty':                  info['qty'],
                'uom':                  info['uom'],
                'last_move_date':       str(last_date) if last_date else None,
                'days_idle':            days_idle,
            })
        stagnant.sort(key=lambda r: r['days_idle'] if r['days_idle'] is not None else 10 ** 6, reverse=True)

        # ── expired products still on hand ──────────────────────────────────
        # Uses product.template.expiration_date (a single date per product,
        # set on the product form) instead of per-lot expiry tracking.
        expired = []
        for pid, info in by_product.items():
            tmpl = info['product'].product_tmpl_id
            exp_date = tmpl.expiration_date
            if not exp_date or exp_date >= today:
                continue
            expired.append({
                'product_id':           pid,
                'product_name':         info['product'].name,
                'product_default_code': info['product'].default_code or '',
                'categ_name':           info['product'].categ_id.name if info['product'].categ_id else '',
                'expiration_date':      str(exp_date),
                'qty':                  info['qty'],
                'uom':                  info['uom'],
                'days_expired':         (today - exp_date).days,
            })
        expired.sort(key=lambda r: r['days_expired'], reverse=True)

        return http_response({
            'days':           days_n,
            'cutoff_date':    str(cutoff),
            'stagnant':       stagnant,
            'expired':        expired,
            'stagnant_count': len(stagnant),
            'expired_count':  len(expired),
        })


# ─────────────────────────────────────────────────────────────────────────────
#  material.purchase.requisition
#  model: material.purchase.requisition  |  lines: material.purchase.requisition.line
#  route prefix: /api/v1/purchase/cr-requisitions
# ─────────────────────────────────────────────────────────────────────────────

def _cr_attachment_list(attachments):
    return [{
        'id':   a.id,
        'name': a.name,
        'url':  f'/web/content/{a.id}?download=true',
    } for a in attachments]


def _build_cr_requisition_vals(body, vals=None):
    vals = vals if vals is not None else {}
    if body.get('employee_id'):
        employee = request.env['hr.employee'].sudo().browse(int(body['employee_id']))
        if employee.exists():
            vals['employee_id'] = employee.id
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
    return vals


def _build_cr_line_vals(lines):
    line_vals_list = []
    for i, line in enumerate(lines):
        if not line.get('product_id'):
            raise ValueError(f'lines[{i}]: product_id is required')
        product = request.env['product.product'].sudo().browse(int(line['product_id']))
        if not product.exists():
            raise ValueError(f'lines[{i}]: product_id not found')

        qty = float(line.get('qty', line.get('quantity', 1)))
        line_val = {
            'product_id': product.id,
            'quantity':   qty,
        }

        if line.get('partner_id'):
            partner = request.env['res.partner'].sudo().browse(int(line['partner_id']))
            if partner.exists():
                line_val['vendor_ids'] = [(4, partner.id)]

        if line.get('request_action') or line.get('requisition_type'):
            line_val['request_action'] = line.get('request_action') or line.get('requisition_type')

        line_vals_list.append((0, 0, line_val))
    return line_vals_list


class CrRequisitionController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        try:
            records = request.env['material.purchase.requisition'].sudo().search([])
            data = []
            for rec in records:
                try:
                    purchase_count = rec.purchase_count
                except Exception:
                    purchase_count = 0
                try:
                    internal_transfer_count = rec.internal_transfer_count
                except Exception:
                    internal_transfer_count = 0
                data.append({
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
                    'purchase_count':               purchase_count,
                    'internal_transfer_count':      internal_transfer_count,
                    'company_id':                   rec.company_id.id if rec.company_id else None,
                    'company_name':                 rec.company_id.name if rec.company_id else None,
                    'request_document_ids':         _cr_attachment_list(rec.request_document_ids),
                    'approval_document_ids':        _cr_attachment_list(rec.approval_document_ids),
                })
            return http_response(data)
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            lines = []
            for line in rec.requisition_lines:
                lines.append({
                    'id':               line.id,
                    'product_id':       line.product_id.id if line.product_id else None,
                    'product_tmpl_id':  line.product_id.product_tmpl_id.id if line.product_id else None,
                    'product_name':     line.product_id.name if line.product_id else None,
                    'default_code':     line.product_id.default_code or '' if line.product_id else '',
                    'standard_price':   line.product_id.standard_price if line.product_id else 0.0,
                    'qty':              line.quantity,
                    'uom_id':           line.unit_of_measure.id if line.unit_of_measure else None,
                    'uom_name':         line.unit_of_measure.name if line.unit_of_measure else None,
                    'vendors':          [{'id': v.id, 'name': v.name} for v in line.vendor_ids],
                    'request_action':   line.request_action or '',
                })

            try:
                purchase_count = rec.purchase_count
            except Exception:
                purchase_count = 0
            try:
                internal_transfer_count = rec.internal_transfer_count
            except Exception:
                internal_transfer_count = 0

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
                'purchase_count':               purchase_count,
                'internal_transfer_count':      internal_transfer_count,
                'company_id':                   rec.company_id.id if rec.company_id else None,
                'company_name':                 rec.company_id.name if rec.company_id else None,
                'request_document_ids':        _cr_attachment_list(rec.request_document_ids),
                'approval_document_ids':       _cr_attachment_list(rec.approval_document_ids),
                'lines':                        lines,
            }
            return http_response(data)
        except Exception as e:
            return http_response({'error': str(e)}, 500)


class CrRequisitionUpdateController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_cr_requisition(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            vals = {}
            if 'source_location_id' in body:
                loc = request.env['stock.location'].sudo().browse(int(body['source_location_id']))
                if loc.exists():
                    vals['source_location_id'] = loc.id
            if 'destination_location_id' in body:
                loc = request.env['stock.location'].sudo().browse(int(body['destination_location_id']))
                if loc.exists():
                    vals['destination_location_id'] = loc.id

            vals = _build_cr_requisition_vals(body, vals)

            if body.get('lines'):
                try:
                    vals['requisition_lines'] = [(5, 0, 0)] + _build_cr_line_vals(body['lines'])
                except ValueError as e:
                    return http_response({'error': str(e)}, 400)

            if vals:
                rec.write(vals)
            return http_response({
                'id':                       rec.id,
                'name':                     rec.name,
                'state':                    rec.state,
                'source_location_id':       rec.source_location_id.id if rec.source_location_id else None,
                'destination_location_id':  rec.destination_location_id.id if rec.destination_location_id else None,
            })
        except Exception as e:
            return http_response({'error': str(e)}, 500)


_CR_ATTACHMENT_FIELDS = {
    'request':  'request_document_ids',
    'approval': 'approval_document_ids',
}


class CrRequisitionAttachmentController(http.Controller):

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/attachments', type='http', auth='user', methods=['POST'], csrf=False)
    def add_attachment(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            body = json.loads(request.httprequest.data or '{}')
            field = _CR_ATTACHMENT_FIELDS.get(body.get('field'))
            if not field:
                return http_response({'error': "field must be 'request' or 'approval'"}, 400)
            data = body.get('data')
            if not data:
                return http_response({'error': 'data (base64) is required'}, 400)
            attachment = request.env['ir.attachment'].sudo().create({
                'name':      body.get('name') or 'attachment',
                'datas':     data,
                'mimetype':  body.get('mimetype') or False,
                'res_model': 'material.purchase.requisition',
                'res_id':    rec.id,
            })
            rec[field] = [(4, attachment.id)]
            return http_response(_cr_attachment_list(rec[field]), 201)
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/attachments/<int:attachment_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def remove_attachment(self, rec_id, attachment_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            field = _CR_ATTACHMENT_FIELDS.get(kw.get('field'))
            if not field:
                return http_response({'error': "field must be 'request' or 'approval'"}, 400)
            rec[field] = [(3, attachment_id)]
            return http_response(_cr_attachment_list(rec[field]))
        except Exception as e:
            return http_response({'error': str(e)}, 500)


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

            vals = _build_cr_requisition_vals(body, {'employee_id': employee.id})

            try:
                vals['requisition_lines'] = _build_cr_line_vals(body['lines'])
            except ValueError as e:
                return http_response({'error': str(e)}, 400)

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

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm(self, rec_id, **kw):
        """Move draft/new → waiting_department_approval — called when user clicks إرسال للمراجعة."""
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state in ('draft', 'new'):
                rec.action_confirm()
            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})
        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/approve', type='http', auth='user', methods=['POST'], csrf=False)
    def approve(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)

            if rec.state == 'waiting_department_approval':
                rec.action_dept_approve()
            elif rec.state in ('draft', 'new'):
                rec.action_confirm()
                rec.action_dept_approve()
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

            rec.write({
                'state':        'rejected',
                'rejected_id':   request.env.user.id,
                'rejected_date': odoo_fields.Date.context_today(rec),
            })

            return http_response({'id': rec.id, 'name': rec.name, 'state': rec.state})

        except Exception as e:
            return http_response({'error': str(e)}, 500)

    @http.route('/api/v1/purchase/cr-requisitions/<int:rec_id>/create-picking-and-po', type='http', auth='user', methods=['POST'], csrf=False)
    def create_picking_and_po(self, rec_id, **kw):
        try:
            rec = request.env['material.purchase.requisition'].sudo().browse(rec_id)
            if not rec.exists():
                return http_response({'error': 'not found'}, 404)
            if rec.state not in ('approved', 'purchase_order_created'):
                return http_response({'error': f'cannot create order in state: {rec.state}'}, 400)

            body = json.loads(request.httprequest.data or '{}')
            lines_param = body.get('lines')  # [{product_id, qty, price_unit, partner_id, uom_id, name}]

            if lines_param is not None:
                # Create PO from the caller-specified lines only, with exact prices
                rec.write({'state': 'purchase_order_created'})
                now_dt = odoo_fields.Datetime.to_string(odoo_fields.Datetime.now())

                by_vendor = {}
                for line in lines_param:
                    partner_id = line.get('partner_id')
                    product_id = line.get('product_id')
                    template_id = line.get('template_id')

                    # Resolve template → default variant when product_id is not provided
                    if not product_id and template_id:
                        tmpl = request.env['product.template'].sudo().browse(int(template_id))
                        if tmpl.exists() and tmpl.product_variant_ids:
                            product_id = tmpl.product_variant_ids[0].id

                    if not partner_id or not product_id:
                        continue

                    by_vendor.setdefault(int(partner_id), []).append({**line, 'product_id': product_id})

                purchase_ids = []
                for partner_id, po_lines in by_vendor.items():
                    order_lines = []
                    for l in po_lines:
                        pid = int(l['product_id'])
                        product = request.env['product.product'].sudo().browse(pid)

                        line_vals = {
                            'product_id':   pid,
                            'product_qty':  float(l.get('qty', 1)),
                            'price_unit':   float(l.get('price_unit', 0)),
                            'name':         l.get('name', '') or (product.name if product.exists() else ''),
                            'date_planned': now_dt,
                        }

                        # UoM: use provided value, else fall back to product's purchase UoM
                        uom_id = l.get('uom_id')
                        if uom_id:
                            line_vals['product_uom_id'] = int(uom_id)
                        elif product.exists():
                            line_vals['product_uom_id'] = (
                                product.uom_po_id.id or product.uom_id.id
                            )

                        order_lines.append((0, 0, line_vals))

                    po = request.env['purchase.order'].sudo().create({
                        'partner_id':        partner_id,
                        'requisition_order': rec.name,
                        'order_line':        order_lines,
                    })
                    purchase_ids.append(po.id)

                return http_response({
                    'id':              rec.id,
                    'name':            rec.name,
                    'state':           rec.state,
                    'pickings':        [],
                    'purchase_orders': purchase_ids,
                })

            # No lines provided — fall back to the model's default action
            result = rec.action_create_picking_and_po()
            return http_response({
                'id':              rec.id,
                'name':            rec.name,
                'state':           rec.state,
                'pickings':        result.get('pickings', []) if isinstance(result, dict) else [],
                'purchase_orders': result.get('purchase_orders', []) if isinstance(result, dict) else [],
            })
        except Exception as e:
            return http_response({'error': str(e)}, 500)