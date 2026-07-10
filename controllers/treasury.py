# -*- coding: utf-8 -*-
import json
from odoo import http, fields as odoo_fields
from odoo.http import request
from .utils import _json

FINANCIAL_CLASS_AR = {
    'cash':         'نقدي',
    'insurance':    'تأمين صحى',
    'state':        'نفقة الدولة',
    'takaful':      'تكافل وكرامة',
    'consultation': 'مشورة',
    'contract':     'تعاقدات',
    'moh':          'وزارة الصحة',
    'staff':        'عاملين',
}

VISIT_TYPE_AR = {
    'outpatient':   'كشف خارجي',
    'inpatient':    'حجز داخلي',
    'emergency':    'طوارئ',
    'consultation': 'استشارة',
}


def _refund_row(rfn, visit=None):
    """Build a treasury row dict for a credit-note (out_refund) move."""
    time_str = ''
    if rfn.invoice_date:
        # invoice_date is a Date; use create_date for time if available
        cd = rfn.create_date
        if cd:
            time_str = f'{cd.hour:02d}:{cd.minute:02d}'

    fin_class = ''
    if visit:
        fin_class = getattr(visit, 'financial_class', '') or ''
    elif rfn.reversed_entry_id:
        orig_visits = request.env['saycare.visit'].sudo().search(
            [('invoice_id', '=', rfn.reversed_entry_id.id)], limit=1
        )
        if orig_visits:
            fin_class = getattr(orig_visits[0], 'financial_class', '') or ''

    return {
        'is_refund':       True,
        'visit_id':        visit.id if visit else None,
        'visit_name':      visit.name if visit else '',
        'time':            time_str,
        'patient_id':      rfn.partner_id.id   if rfn.partner_id else None,
        'patient_name':    rfn.partner_id.name if rfn.partner_id else '—',
        'mrn':             getattr(rfn.partner_id, 'mrn', '')       if rfn.partner_id else '',
        'national_id':     getattr(rfn.partner_id, 'id_number', '') if rfn.partner_id else '',
        'mobile':          rfn.partner_id.phone if rfn.partner_id else '',
        'clinic':          visit.specialty_id.name if (visit and visit.specialty_id) else '',
        'doctor':          visit.doctor_id.name    if (visit and visit.doctor_id)    else '',
        'visit_type':      VISIT_TYPE_AR.get(visit.visit_type or '', '') if visit else '',
        'financial_class': fin_class,
        'financial_label': FINANCIAL_CLASS_AR.get(fin_class, ''),
        'payment_method':  'cash',
        'state':           'refunded',
        'invoice_id':      rfn.id,
        'invoice_name':    rfn.name or '',
        'invoice_state':   rfn.state,
        'payment_state':   'refunded',
        'amount_total':    -rfn.amount_total,   # negative → shown in red
        'amount_due':      0.0,
        'insurance_share': 0.0,
        'patient_share':   0.0,
        'refund_reason':   rfn.narration or '',
        'original_invoice_name': rfn.reversed_entry_id.name if rfn.reversed_entry_id else '',
    }


class TreasuryController(http.Controller):

    @http.route('/saycare/api/treasury', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, date='', **kw):
        """
        Returns all visits for the given date with their invoice & payment info,
        plus any refund (credit-note) rows created on that date.
        date: YYYY-MM-DD  (defaults to today)
        """
        from odoo.fields import Date as D
        target = date or str(D.today())

        visits = request.env['saycare.visit'].sudo().search([
            ('admission_date', '>=', f'{target} 00:00:00'),
            ('admission_date', '<=', f'{target} 23:59:59'),
            ('invoice_id',     '!=', False),
        ], order='admission_date desc')

        rows = []
        for v in visits:
            inv = getattr(v, 'invoice_id', None) or None
            payment_state = inv.payment_state  if inv else ''
            amount_total  = inv.amount_total   if inv else 0.0
            amount_due    = inv.amount_residual if inv else 0.0

            fin_class   = getattr(v, 'financial_class', 'cash') or 'cash'
            v_insurance = getattr(v, 'insurance_share', 0.0) or 0.0
            if fin_class == 'cash':
                v_insurance = 0.0
            v_patient = max(0.0, amount_total - v_insurance)

            admission_dt = v.admission_date
            time_str = ''
            if admission_dt:
                time_str = f'{admission_dt.hour:02d}:{admission_dt.minute:02d}'

            # ── check if invoice has been reversed (refunded) ─────────────────
            # payment_state='reversed' only fires when Odoo auto-reconciles;
            # when invoice was already paid we must check for a linked credit note.
            rfn_move = None
            if inv:
                rfn_move = request.env['account.move'].sudo().search([
                    ('reversed_entry_id', '=', inv.id),
                    ('move_type', '=', 'out_refund'),
                    ('state', '=', 'posted'),
                ], limit=1)
            is_reversed = bool(rfn_move) or payment_state == 'reversed'
            refund_reason = ''
            if is_reversed:
                refund_reason = (rfn_move.narration or '') if rfn_move else ''
                amount_total = -amount_total  # display as negative

            rows.append({
                'is_refund':               is_reversed,
                'visit_id':          v.id,
                'visit_name':        v.name or '',
                'time':              time_str,
                'patient_id':        v.patient_id.id   if v.patient_id else None,
                'patient_name':      v.patient_id.name if v.patient_id else '—',
                'mrn':               getattr(v.patient_id, 'mrn',       '') if v.patient_id else '',
                'national_id':       getattr(v.patient_id, 'id_number', '') if v.patient_id else '',
                'mobile':            v.patient_id.phone if v.patient_id else '',
                'clinic':            v.specialty_id.name if v.specialty_id else '',
                'doctor':            v.doctor_id.name    if v.doctor_id   else '',
                'visit_type':        VISIT_TYPE_AR.get(v.visit_type or '', v.visit_type or ''),
                'financial_class':   getattr(v, 'financial_class', '') or '',
                'financial_label':   FINANCIAL_CLASS_AR.get(getattr(v, 'financial_class', '') or '', ''),
                'payment_method':    getattr(v, 'payment_method', 'cash') or 'cash',
                'state':             'refunded' if is_reversed else v.state,
                'invoice_id':        inv.id            if inv else None,
                'invoice_name':      inv.name          if inv else '',
                'invoice_state':     inv.state         if inv else '',
                'payment_state':     'refunded' if is_reversed else payment_state,
                'amount_total':      amount_total,
                'amount_due':        amount_due,
                'insurance_share':   v_insurance,
                'patient_share':     v_patient,
                'refund_reason':     refund_reason,
            })

        # summary totals
        positive_rows  = [r for r in rows if r['amount_total'] > 0]
        total_amount   = sum(r['amount_total'] for r in positive_rows)
        cash_amount    = sum(r['amount_total'] for r in positive_rows if r['financial_class'] == 'cash')
        refunded_total = sum(abs(r['amount_total']) for r in rows if r['is_refund'])

        return _json({
            'date':           target,
            'rows':           rows,
            'total_visits':   len(positive_rows),
            'total_amount':   total_amount,
            'cash_amount':    cash_amount,
            'refunded_total': refunded_total,
        })

    # ── POST /saycare/api/treasury/refund ─────────────────────────────────────
    @http.route('/saycare/api/treasury/refund', type='http', auth='user', methods=['POST'], csrf=False)
    def create_refund(self, **kw):
        """
        Create a credit note (استرداد) for a paid invoice.
        Body JSON:
          invoice_id  – int, required
          amount      – float, required (≤ invoice amount_total)
          method      – 'cash' | 'wallet' | 'credit'   (default: cash)
          reason      – str, optional cancellation reason
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _json({'error': 'invalid JSON'}, 400)

        invoice_id = body.get('invoice_id')
        amount     = float(body.get('amount') or 0)
        method     = body.get('method', 'cash')
        reason     = body.get('reason', '')

        if not invoice_id:
            return _json({'error': 'invoice_id is required'}, 400)
        if amount <= 0:
            return _json({'error': 'amount must be > 0'}, 400)

        inv = request.env['account.move'].sudo().browse(int(invoice_id))
        if not inv.exists() or inv.move_type != 'out_invoice':
            return _json({'error': 'invoice not found'}, 404)
        if inv.state != 'posted':
            return _json({'error': 'invoice must be posted before refunding'}, 400)

        # ── this specific invoice can only be refunded once ───────────────────
        already_refunded = request.env['account.move'].sudo().search_count([
            ('reversed_entry_id', '=', inv.id),
            ('move_type', '=', 'out_refund'),
            ('state', '=', 'posted'),
        ])
        if already_refunded:
            return _json({
                'error': 'تم استرداد مبلغ لهذه الفاتورة من قبل، لا يمكن الاسترداد مرة أخرى',
            }, 400)

        today = odoo_fields.Date.today()

        # ── build credit-note lines proportionally if partial refund ─────────
        ratio = min(amount / inv.amount_total, 1.0) if inv.amount_total else 1.0
        line_vals = []
        for line in inv.invoice_line_ids:
            if line.display_type not in ('product', False, ''):
                continue
            line_vals.append((0, 0, {
                'name':       line.name or '',
                'quantity':   line.quantity,
                'price_unit': round(line.price_unit * ratio, 6),
                'product_id': line.product_id.id if line.product_id else False,
                'tax_ids':    [(6, 0, line.tax_ids.ids)],
            }))

        if not line_vals:
            # fallback: single generic line
            line_vals = [(0, 0, {
                'name':       f'استرداد - {inv.name}',
                'quantity':   1,
                'price_unit': amount,
            })]

        refund = request.env['account.move'].sudo().create({
            'move_type':          'out_refund',
            'partner_id':         inv.partner_id.id if inv.partner_id else False,
            'invoice_date':       today,
            'ref':                inv.name or '',
            'narration':          reason or f'استرداد من {inv.name}',
            'journal_id':         inv.journal_id.id,
            'reversed_entry_id':  inv.id,
            'invoice_line_ids':   line_vals,
        })
        refund.action_post()

        # ── register payment for cash refunds — via the standard Register
        # Payment wizard (same mechanism invoices.py uses for invoice payments)
        # so this shows up as a real account.payment, not just a reconciled
        # manual journal entry.
        #
        # action_post() above may have already auto-reconciled this credit
        # note against the original invoice's own receivable line (e.g. when
        # that invoice was never actually paid — there's nothing to hand back
        # in cash, the credit note just voids it). In that case amount_residual
        # is already 0 and there is nothing left to register a payment for.
        # ───────────────────────────────────────────────────────────────────
        if method == 'cash' and refund.amount_residual:
            cash_journal = request.env['account.journal'].sudo().search([
                ('type', '=', 'cash'),
                ('company_id', '=', refund.company_id.id),
            ], limit=1)
            if not cash_journal:
                cash_journal = request.env['account.journal'].sudo().search([
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', refund.company_id.id),
                ], limit=1)

            if cash_journal:
                wizard = request.env['account.payment.register'].sudo().with_context(
                    active_model='account.move',
                    active_ids=[refund.id],
                    active_id=refund.id,
                ).create({
                    'journal_id':    cash_journal.id,
                    'amount':        refund.amount_residual,
                    'payment_date':  today,
                    'communication': refund.name or '',
                })
                wizard.action_create_payments()
                request.env.flush_all()
                refund.invalidate_recordset()

        # ── cancel the underlying visit (and its appointment) regardless of
        # whether the page that requested this refund already did so - Dr/Nurse's
        # own cancel-visit call can fail/race independently of the refund itself,
        # so this is the single authoritative place that guarantees a refunded
        # visit disappears from the nurse/doctor queues. ─────────────────────
        visit = request.env['saycare.visit'].sudo().search(
            [('invoice_id', '=', inv.id)], limit=1
        )
        if visit and visit.state != 'cancelled':
            visit.write({'state': 'cancelled'})
            linked_appt = request.env['saycare.appointment'].sudo().search(
                [('visit_id', '=', visit.id), ('state', '!=', 'cancelled')], limit=1
            )
            if linked_appt:
                linked_appt.write({'state': 'cancelled'})

        # ── this refund fulfills any pending Dr/Nurse refund request for the
        # same visit/invoice - clear it so it stops showing as "pending" ─────
        request.env['saycare.refund.request'].sudo().search([
            '|', ('invoice_id', '=', inv.id), ('visit_id', '=', visit.id if visit else False),
        ]).unlink()

        return _json({
            'ok':            True,
            'refund_id':     refund.id,
            'refund_name':   refund.name or '',
            'amount':        refund.amount_total,
            'invoice_id':    inv.id,
            'payment_state': inv.payment_state,
        }, 201)
