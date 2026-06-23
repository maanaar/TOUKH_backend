# -*- coding: utf-8 -*-
import json as _json_mod
import json
import logging
from odoo import http, fields
from odoo.http import request
from odoo.fields import Datetime as DT
from .utils import _json, _patient_dict

_logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    'waiting':      ['triage', 'doctor_queue', 'cancelled'],
    'triage':       ['doctor_queue', 'cancelled'],
    'doctor_queue': ['in_progress', 'cancelled'],
    'in_progress':  ['done', 'cancelled'],
    'done':         [],
    'cancelled':    [],
}


def _visit_dict(v, full=False):
    from .vitals import _vitals_dict
    from .clinical_notes import _note_dict
    from .medications import _med_dict
    from .lab_orders import _lab_dict
    from .rad_orders import _rad_dict

    d = {
        'id':              v.id,
        'name':            v.name or '',
        'state':           v.state,
        'visit_type':      v.visit_type or '',
        'financial_class': v.financial_class or '',
        'payment_method':  v.payment_method  or 'cash',
        'chief_complaint': v.chief_complaint or '',
        'triage_notes':    v.triage_notes or '',
        'admission_date':  str(v.admission_date) if v.admission_date else None,
        'discharge_date':  str(v.discharge_date) if v.discharge_date else None,
        'patient_id':          v.patient_id.id if v.patient_id else None,
        'patient_name':        v.patient_id.name if v.patient_id else '',
        'patient_mrn':         getattr(v.patient_id, 'mrn', '') if v.patient_id else '',
        'patient_national_id': getattr(v.patient_id, 'id_number', '') or '' if v.patient_id else '',
        'patient_mobile':      getattr(v.patient_id, 'phone', '') or '' if v.patient_id else '',
        'doctor_id':       v.doctor_id.id if v.doctor_id else None,
        'doctor_name':     v.doctor_id.name if v.doctor_id else '',
        'nurse_id':        v.nurse_id.id if v.nurse_id else None,
        'nurse_name':      v.nurse_id.name if v.nurse_id else '',
        'specialty_id':    v.specialty_id.id if v.specialty_id else None,
        'specialty_name':  v.specialty_id.name if v.specialty_id else '',
        'notes':           v.notes or '',
        'services': [{
            'id':              s.id,
            'name':            s.name,
            'price':           s.price,
            'insurance_price': s.insurance_price,
            'visit_type':      s.visit_type or '',
        } for s in v.service_ids],
        'basket':          _json_mod.loads(v.basket_json or '[]') if v.basket_paid else [],
        'basket_pending':  _json_mod.loads(v.basket_json or '[]') if not v.basket_paid else [],
        'invoice_id':      v.invoice_id.id if v.invoice_id else None,
        'total_price':     v.total_price,
        'insurance_share': v.insurance_share,
        'patient_share':   v.patient_share,
    }
    if full:
        d['patient']           = _patient_dict(v.patient_id) if v.patient_id else {}
        d['vitals']            = [_vitals_dict(vs) for vs in v.vital_sign_ids]
        d['medication_orders'] = [_med_dict(m) for m in v.medication_order_ids]
        d['lab_orders']        = [_lab_dict(lo) for lo in v.lab_order_ids]
        d['rad_orders']        = [_rad_dict(ro) for ro in v.rad_order_ids]
        note = v.clinical_note_ids[:1]
        d['clinical_note']     = _note_dict(note[0]) if note else None
    return d


class VisitListController(http.Controller):

    @http.route('/saycare/api/visits', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, date='', date_from='', date_to='', state='', specialty_id='',
                doctor_id='', patient_id='', visit_type='', **kw):
        domain = []
        if date:
            domain += [('admission_date', '>=', f'{date} 00:00:00'),
                       ('admission_date', '<=', f'{date} 23:59:59')]
        else:
            if date_from:
                domain.append(('admission_date', '>=', f'{date_from} 00:00:00'))
            if date_to:
                domain.append(('admission_date', '<=', f'{date_to} 23:59:59'))
        if state:
            states = [s.strip() for s in state.split(',') if s.strip()]
            domain.append(('state', 'in', states) if len(states) > 1 else ('state', '=', states[0]))
        if specialty_id:
            domain.append(('specialty_id', '=', int(specialty_id)))
        if doctor_id:
            domain.append(('doctor_id', '=', int(doctor_id)))
        if patient_id:
            domain.append(('patient_id', '=', int(patient_id)))
        if visit_type:
            domain.append(('visit_type', '=', visit_type))
        records = request.env['saycare.visit'].sudo().search(
            domain, order='admission_date desc', limit=200
        )
        return _json([_visit_dict(v) for v in records])


class VisitController(http.Controller):

    @http.route('/saycare/api/visit', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        if not body.get('patient_id'):
            return _json({'error': 'patient_id is required'}, 400)
        vals = {
            'patient_id':      body['patient_id'],
            'visit_type':      body.get('visit_type', 'outpatient'),
            'financial_class': body.get('financial_class', ''),
            'payment_method':  body.get('payment_method', 'cash'),
            'chief_complaint': body.get('chief_complaint', ''),
            'specialty_id':    body.get('specialty_id'),
            'doctor_id':       body.get('doctor_id'),
            'notes':           body.get('notes', ''),
            # financial details
            'decision_no':       body.get('decision_no', ''),
            'expiry_date':       body.get('expiry_date') or False,
            'available_balance': float(body['available_balance']) if body.get('available_balance') else 0.0,
            'covered_services':  body.get('covered_services', ''),
            'contract_entity':   body.get('contract_entity', ''),
            'co_pay_percent':    body.get('co_pay_percent', ''),
            'approval_required': bool(body.get('approval_required', False)),
            'admin_letter_no':   body.get('admin_letter_no', ''),
            'issuing_authority': body.get('issuing_authority', ''),
            'card_number':       body.get('card_number', ''),
            'financial_notes':   body.get('financial_notes', ''),
            'employee_id_no':    body.get('employee_id', ''),
            'department':        body.get('department', ''),
        }
        service_ids = body.get('service_ids', [])
        if service_ids:
            vals['service_ids'] = [(6, 0, service_ids)]

        # ── duplication guard: same patient + specialty + today, still open ──
        from odoo.fields import Date as D
        today = D.today()
        dup = request.env['saycare.visit'].sudo().search([
            ('patient_id',  '=', body['patient_id']),
            ('specialty_id','=', body.get('specialty_id')),
            ('state', 'not in', ['done', 'cancelled']),
            ('admission_date', '>=', f'{today} 00:00:00'),
            ('admission_date', '<=', f'{today} 23:59:59'),
        ], limit=1)
        _logger.info('VISIT CREATE skip_invoice=%s specialty=%s patient=%s dup=%s',
                     body.get('skip_invoice'), body.get('specialty_id'),
                     body.get('patient_id'), dup.id if dup else None)

        if dup:
            if service_ids:
                dup.write({'service_ids': [(6, 0, service_ids)]})
            # If this is a secondary clinic (skip_invoice), remove any old invoice
            if body.get('skip_invoice'):
                old_inv = dup.invoice_id
                if old_inv and old_inv.exists():
                    try:
                        with request.env.cr.savepoint():
                            if old_inv.state == 'posted':
                                old_inv.button_cancel()
                            old_inv.unlink()
                            dup.write({'invoice_id': False})
                    except Exception:
                        pass
                result = _visit_dict(dup)
                result['invoice_id'] = None
                return _json(result, 200)
            return _json(_visit_dict(dup), 200)

        visit = request.env['saycare.visit'].sudo().create(vals)
        if body.get('appointment_id'):
            appt = request.env['saycare.appointment'].sudo().browse(body['appointment_id'])
            if appt.exists():
                appt.write({'visit_id': visit.id, 'state': 'arrived'})

        invoice_id = None
        if not body.get('skip_invoice'):
            try:
                with request.env.cr.savepoint():
                    invoice_id = _create_visit_invoice(visit)
                    if invoice_id:
                        visit.write({'invoice_id': invoice_id})
            except Exception:
                pass
        result = _visit_dict(visit)
        result['invoice_id'] = invoice_id
        return _json(result, 201)

    @http.route('/saycare/api/visit/<int:visit_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)
        return _json(_visit_dict(v, full=True))

    @http.route('/saycare/api/visit/<int:visit_id>/ensure_invoice', type='http', auth='user', methods=['POST'], csrf=False)
    def ensure_invoice(self, visit_id, **kw):
        """Get or create an invoice for this visit. Returns invoice_id (may be None if no journal found)."""
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)

        invoice_id = v.invoice_id.id if (v.invoice_id and v.invoice_id.exists()) else None

        if not invoice_id:
            try:
                with request.env.cr.savepoint():
                    invoice_id = _create_visit_invoice(v)
                    if invoice_id:
                        v.write({'invoice_id': invoice_id})
            except Exception:
                pass

        inv = request.env['account.move'].sudo().browse(invoice_id) if invoice_id else None
        return _json({
            'invoice_id':      invoice_id,
            'financial_class': v.financial_class or 'cash',
            'patient_mrn':     getattr(v.patient_id, 'mrn', '') if v.patient_id else '',
            'patient_name':    v.patient_id.name if v.patient_id else '',
            'amount':          inv.amount_total if (inv and inv.exists()) else 0.0,
            'invoice_state':   inv.state if (inv and inv.exists()) else '',
            'payment_state':   inv.payment_state if (inv and inv.exists()) else '',
        })

    @http.route('/saycare/api/visit/<int:visit_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_services(self, visit_id, **kw):
        """Update service_ids on an existing visit and regenerate its invoice."""
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        service_ids   = body.get('service_ids', [])
        skip_invoice  = bool(body.get('skip_invoice'))
        _logger.info('VISIT UPDATE id=%s skip_invoice=%s', visit_id, skip_invoice)
        v.write({'service_ids': [(6, 0, service_ids)]})

        # Cancel + delete old invoice.
        # For skip_invoice visits: always remove the old invoice (it should not exist).
        # For primary visits: remove so a fresh one can be created below.
        old_inv = v.invoice_id
        if old_inv and old_inv.exists():
            try:
                with request.env.cr.savepoint():
                    if old_inv.state == 'posted':
                        old_inv.button_cancel()
                    old_inv.unlink()
            except Exception:
                pass
            v.write({'invoice_id': False})   # always clear the FK, even if unlink failed

        invoice_id = None
        if not skip_invoice:
            try:
                with request.env.cr.savepoint():
                    invoice_id = _create_visit_invoice(v)
                    if invoice_id:
                        v.write({'invoice_id': invoice_id})
            except Exception:
                pass

        result = _visit_dict(v)
        result['invoice_id'] = invoice_id
        return _json(result, 200)

    @http.route('/saycare/api/visit/<int:visit_id>/basket', type='http', auth='user', methods=['GET'], csrf=False)
    def get_basket(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'not found'}, 404)
        return _json({'basket': _json_mod.loads(v.basket_json or '[]')})

    @http.route('/saycare/api/visit/<int:visit_id>/basket', type='http', auth='user', methods=['POST'], csrf=False)
    def set_basket(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '[]')
        except Exception:
            return _json({'error': 'invalid JSON'}, 400)
        items = body if isinstance(body, list) else body.get('basket', [])
        v.write({'basket_json': _json_mod.dumps(items)})
        return _json({'basket': items})

    @http.route('/saycare/api/visit/<int:visit_id>/basket', type='http', auth='user', methods=['DELETE'], csrf=False)
    def clear_basket(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'not found'}, 404)
        v.write({'basket_json': '[]', 'basket_paid': False})
        return _json({'ok': True})

    @http.route('/saycare/api/visit/<int:visit_id>/basket/mark-paid', type='http', auth='user', methods=['POST'], csrf=False)
    def mark_basket_paid(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'not found'}, 404)
        v.write({'basket_paid': True})
        return _json({'ok': True})

    @http.route('/saycare/api/visit/<int:visit_id>/state', type='http', auth='user', methods=['POST'], csrf=False)
    def change_state(self, visit_id, **kw):
        v = request.env['saycare.visit'].sudo().browse(visit_id)
        if not v.exists():
            return _json({'error': 'visit not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)
        new_state = body.get('state')
        if new_state not in VALID_TRANSITIONS.get(v.state, []):
            return _json({'error': f'cannot transition from {v.state} to {new_state}'}, 400)
        vals = {'state': new_state}
        if body.get('nurse_id'):
            vals['nurse_id'] = body['nurse_id']
        if body.get('triage_notes'):
            vals['triage_notes'] = body['triage_notes']
        if body.get('chief_complaint'):
            vals['chief_complaint'] = body['chief_complaint']
        if new_state == 'done':
            vals['discharge_date'] = DT.now()
        v.write(vals)

        invoice_id = None
        if new_state == 'done' and v.service_ids and v.patient_id:
            invoice_id = _create_visit_invoice(v)

        return _json({
            'ok': True,
            'state': v.state,
            'discharge_date': str(v.discharge_date) if v.discharge_date else None,
            'invoice_id': invoice_id,
        })


class ClinicBookingController(http.Controller):
    """
    POST /saycare/api/clinic-booking
    One-shot: create (or find) patient → appointment → visit with services.
    Returns { visit_id, appointment_id, total_price, patient_share, invoice_id }
    """

    @http.route('/saycare/api/clinic-booking', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        env = request.env

        # ── 1. resolve patient ────────────────────────────────────────────────
        patient_id = body.get('patient_id')
        if not patient_id:
            id_number = body.get('id_number', '').strip()
            patient = env['res.partner'].sudo().search(
                [('id_number', '=', id_number), ('is_patient', '=', True)], limit=1
            ) if id_number else env['res.partner']
            if not patient:
                if not body.get('patient_name'):
                    return _json({'error': 'patient_id or patient_name required'}, 400)
                patient = env['res.partner'].sudo().create({
                    'name':           body['patient_name'],
                    'id_number':      id_number,
                    'phone':          body.get('mobile', ''),
                    'is_patient':     True,
                    'financial_class': body.get('financial_class', 'cash'),
                })
            patient_id = patient.id

        # ── 2. service IDs (only saycare.service numeric IDs) ─────────────────
        raw_service_ids = body.get('service_ids', [])
        service_ids = [int(s) for s in raw_service_ids
                       if str(s).isdigit() or (isinstance(s, int))]

        # ── 3. create appointment ─────────────────────────────────────────────
        specialty_id = body.get('specialty_id')
        doctor_id    = body.get('doctor_id')
        booking_date = body.get('booking_date', str(fields.Date.today()))
        start_time   = body.get('start_time', 8.0)

        appt_vals = {
            'patient_id':  patient_id,
            'date':        booking_date,
            'start_time':  float(start_time),
            'end_time':    float(start_time) + 0.25,
            'visit_type':  'outpatient',
            'state':       'confirmed',
        }
        if specialty_id:
            appt_vals['specialty_id'] = int(specialty_id)
        if doctor_id:
            appt_vals['doctor_id'] = int(doctor_id)
        appt = env['saycare.appointment'].sudo().create(appt_vals)

        # ── 4. create visit with services ─────────────────────────────────────
        visit_vals = {
            'patient_id':      patient_id,
            'visit_type':      'outpatient',
            'financial_class': body.get('financial_class', 'cash'),
            'payment_method':  body.get('payment_method', 'cash'),
            'chief_complaint': body.get('chief_complaint', ''),
            'notes':           body.get('notes', ''),
        }
        if specialty_id:
            visit_vals['specialty_id'] = int(specialty_id)
        if doctor_id:
            visit_vals['doctor_id'] = int(doctor_id)
        if service_ids:
            visit_vals['service_ids'] = [(6, 0, service_ids)]

        visit = env['saycare.visit'].sudo().create(visit_vals)
        appt.write({'visit_id': visit.id, 'state': 'arrived'})

        # ── 5. create invoice immediately ─────────────────────────────────────
        invoice_id     = None
        invoice_name   = None
        invoice_amount = visit.patient_share
        if visit.service_ids:
            invoice_id = _create_visit_invoice(visit)
            if invoice_id:
                inv = env['account.move'].sudo().browse(invoice_id)
                invoice_name = inv.name or ''

        return _json({
            'visit_id':        visit.id,
            'visit_name':      visit.name,
            'appointment_id':  appt.id,
            'patient_id':      patient_id,
            'total_price':     visit.total_price,
            'insurance_share': visit.insurance_share,
            'patient_share':   visit.patient_share,
            'invoice_id':      invoice_id,
            'invoice_name':    invoice_name,
            'invoice_amount':  invoice_amount,
            'services':        [{'id': s.id, 'name': s.name, 'price': s.price,
                                 'insurance_price': s.insurance_price}
                                for s in visit.service_ids],
        }, 201)


FINANCIAL_LABELS = {
    'cash':         'نقدي',
    'insurance':    'تأمين صحى',
    'state':        'نفقة الدولة',
    'takaful':      'تكافل وكرامة',
    'consultation': 'مشورة',
    'contract':     'تعاقدات',
    'moh':          'وزارة الصحة',
    'staff':        'عاملين',
}

VISIT_TYPE_LABELS = {
    'outpatient':   'كشف خارجي',
    'inpatient':    'حجز داخلي',
    'emergency':    'طوارئ',
    'consultation': 'استشارة',
}

# Financial classes where the patient pays the full amount immediately (cash جورنال)
IMMEDIATE_PAYMENT_CLASSES = ('cash', 'takaful')

# Financial classes where insurance covers part of the cost
INSURANCE_SPLIT_CLASSES = ('insurance', 'contract', 'moh', 'state', 'staff', 'consultation')


def _create_visit_invoice(visit):
    env = visit.env

    # ── duplication guard ─────────────────────────────────────────────────────
    existing = env['account.move'].sudo().search([
        ('move_type', '=', 'out_invoice'),
        ('narration', 'like', visit.name),
        ('partner_id', '=', visit.patient_id.id),
    ], limit=1)
    if existing:
        return existing.id

    company    = env.company
    fin_class  = visit.financial_class or 'cash'
    is_cash    = fin_class == 'cash'

    # ── Resolve the journal for this financial_class ──────────────────────────
    # Only use the journal that is tagged with this exact وجهة مالية.
    # If none exists → skip invoice creation entirely.
    journal = env['account.journal'].sudo().search([
        ('financial_class', '=', fin_class),
        ('company_id', '=', company.id),
    ], limit=1)
    if not journal:
        return None

    financial_label  = FINANCIAL_LABELS.get(fin_class, fin_class)
    visit_type_label = VISIT_TYPE_LABELS.get(visit.visit_type or '', 'زيارة طبية')

    # ── Build invoice lines ───────────────────────────────────────────────────
    # نقدي: patient pays full price → insurance account (حساب التأمين) = 0
    # Others: split patient_share and insurance_share into separate lines
    lines = []
    for svc in visit.service_ids:
        product = env['product.product'].sudo().search([
            ('name', '=', svc.name), ('type', '=', 'service'),
        ], limit=1)

        if is_cash:
            # Full price on one line; no insurance split → حساب التأمين = 0
            lines.append((0, 0, {
                'name':         svc.name,
                'quantity':     1,
                'price_unit':   svc.price,
                'product_id':   product.id if product else False,
                'display_type': 'product',
            }))
        else:
            patient_share   = max(0.0, svc.price - svc.insurance_price)
            insurance_share = svc.insurance_price or 0.0

            # Patient co-pay line
            if patient_share > 0:
                lines.append((0, 0, {
                    'name':         f'{svc.name} — حصة المريض',
                    'quantity':     1,
                    'price_unit':   patient_share,
                    'product_id':   product.id if product else False,
                    'display_type': 'product',
                }))
            # Insurance coverage line (حساب التأمين)
            if insurance_share > 0:
                lines.append((0, 0, {
                    'name':         f'{svc.name} — حصة التأمين ({financial_label})',
                    'quantity':     1,
                    'price_unit':   insurance_share,
                    'product_id':   product.id if product else False,
                    'display_type': 'product',
                }))
            # If both shares are 0, fall back to full price
            if patient_share == 0 and insurance_share == 0:
                lines.append((0, 0, {
                    'name':         svc.name,
                    'quantity':     1,
                    'price_unit':   svc.price,
                    'product_id':   product.id if product else False,
                    'display_type': 'product',
                }))

    # Always include at least one descriptive line
    if not lines:
        lines.append((0, 0, {
            'name':         f'{visit_type_label} — {visit.specialty_id.name or ""} — {financial_label}',
            'quantity':     1,
            'price_unit':   0.0,
            'display_type': 'product',
        }))

    move = env['account.move'].sudo().create({
        'move_type':        'out_invoice',
        'partner_id':       visit.patient_id.id,
        'journal_id':       journal.id,
        'currency_id':      company.currency_id.id,
        'invoice_line_ids': lines,
        'narration':        f'زيارة {visit.name} — {visit_type_label} — {financial_label}',
    })

    # Post invoice unconditionally (zero-amount invoices are valid in Odoo)
    try:
        with env.cr.savepoint():
            move.action_post()
    except Exception:
        return move.id  # return draft id if posting fails — caller can retry

    return move.id
