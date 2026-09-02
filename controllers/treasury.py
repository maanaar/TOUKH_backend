# -*- coding: utf-8 -*-
import json
from zoneinfo import ZoneInfo
from odoo import http, fields as odoo_fields
from odoo.http import request
from odoo.tools.mail import html2plaintext
from .utils import _json

_CAIRO_TZ = ZoneInfo('Africa/Cairo')


def _to_cairo(dt):
    """Odoo stores/returns naive UTC datetimes - the container runs on UTC
    (no TZ set in docker-compose), so displaying dt.hour/.minute directly
    shows the raw UTC hour mislabeled as local time. Convert explicitly."""
    if not dt:
        return None
    return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(_CAIRO_TZ)

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
        cd = _to_cairo(rfn.create_date)
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
        'refund_reason':   html2plaintext(rfn.narration) if rfn.narration else '',
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

            # "الوقت" should reflect when the money was actually collected, not
            # when the visit record was created — admission_date can be set
            # well before payment (e.g. emergency intake, or a pending request
            # sitting in الخزنة before being confirmed). Prefer the reconciled
            # account.payment's own timestamp whenever the invoice is paid.
            time_dt = None
            if inv and payment_state == 'paid':
                payment = request.env['account.payment'].sudo().search(
                    [('reconciled_invoice_ids', 'in', inv.id)], order='create_date desc', limit=1
                )
                if payment and payment.create_date:
                    time_dt = payment.create_date
            if not time_dt:
                time_dt = v.admission_date
            time_dt = _to_cairo(time_dt)
            time_str = f'{time_dt.hour:02d}:{time_dt.minute:02d}' if time_dt else ''

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
                refund_reason = (html2plaintext(rfn_move.narration) if rfn_move.narration else '') if rfn_move else ''
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

        # ── Inpatient Open Bill discharge invoices ──────────────────────────
        # These never get linked onto a saycare.visit — they're generated
        # straight from the admission's own sale_order_id at discharge (see
        # AdmissionRequestController.discharge) — so the visit-based query
        # above never finds them. Without this, a discharged patient's bill
        # would only ever be payable from فواتير المرضى, never from الخزنة's
        # own daily list where cashiers actually work day to day.
        admissions = request.env['saycare.admission.request'].sudo().search([
            ('discharge_date', '>=', f'{target} 00:00:00'),
            ('discharge_date', '<=', f'{target} 23:59:59'),
            ('sale_order_id',  '!=', False),
        ])
        for adm in admissions:
            for inv in adm.sale_order_id.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice'):
                payment_state = inv.payment_state
                amount_total  = inv.amount_total
                amount_due    = inv.amount_residual

                time_dt = None
                if payment_state == 'paid':
                    payment = request.env['account.payment'].sudo().search(
                        [('reconciled_invoice_ids', 'in', inv.id)], order='create_date desc', limit=1
                    )
                    if payment and payment.create_date:
                        time_dt = payment.create_date
                if not time_dt:
                    time_dt = adm.discharge_date
                time_dt = _to_cairo(time_dt)
                time_str = f'{time_dt.hour:02d}:{time_dt.minute:02d}' if time_dt else ''

                rfn_move = request.env['account.move'].sudo().search([
                    ('reversed_entry_id', '=', inv.id),
                    ('move_type', '=', 'out_refund'),
                    ('state', '=', 'posted'),
                ], limit=1)
                is_reversed = bool(rfn_move) or payment_state == 'reversed'
                refund_reason = ''
                if is_reversed:
                    refund_reason = html2plaintext(rfn_move.narration) if (rfn_move and rfn_move.narration) else ''
                    amount_total = -amount_total

                rows.append({
                    'is_refund':       is_reversed,
                    'visit_id':        adm.visit_id.id if adm.visit_id else None,
                    'visit_name':      adm.inpatient_booking_number or adm.sale_order_id.name or '',
                    'time':            time_str,
                    'patient_id':      adm.patient_id.id if adm.patient_id else None,
                    'patient_name':    adm.patient_id.name if adm.patient_id else (adm.patient_name or '—'),
                    'mrn':             adm.patient_mrn or '',
                    'national_id':     adm.national_id or '',
                    'mobile':          adm.patient_mobile or '',
                    'clinic':          adm.department_id.display_name if adm.department_id else '',
                    'doctor':          adm.attending_doctor or '',
                    'visit_type':      'فاتورة إقامة (داخلي)',
                    'financial_class': 'cash',
                    'financial_label': adm.payment_type or FINANCIAL_CLASS_AR.get('cash', ''),
                    'payment_method':  'cash',
                    'state':           'refunded' if is_reversed else inv.state,
                    'invoice_id':      inv.id,
                    'invoice_name':    inv.name or '',
                    'invoice_state':   inv.state,
                    'payment_state':   'refunded' if is_reversed else payment_state,
                    'amount_total':    amount_total,
                    'amount_due':      amount_due,
                    'insurance_share': 0.0,
                    'patient_share':   amount_total,
                    'refund_reason':   refund_reason,
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
        # Row-lock the invoice for the rest of this transaction before checking:
        # without this, two concurrent refund requests for the same invoice
        # (double-click across tabs, a retried request) could both pass the
        # "already refunded?" check before either one's credit note commits,
        # producing two credit notes for one invoice. The lock makes the second
        # request wait until the first transaction commits (or rolls back), by
        # which point its own check will correctly see the first refund.
        request.env.cr.execute(
            "SELECT id FROM account_move WHERE id = %s FOR UPDATE", (inv.id,)
        )
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

        # ── full-refund native reversal ────────────────────────────────────────
        # Only attempted for a FULL refund (ratio >= 1) of an already-paid
        # invoice — a partial refund genuinely isn't "reversed", it's still
        # partially paid, so the invoice correctly stays 'paid'/'partial' there.
        # Standard Odoo "Reverse" behavior: unreconcile the invoice from its
        # existing payment first, so the credit note's own auto-reconcile-on-post
        # links against the INVOICE itself (payment_state -> 'reversed' natively)
        # instead of against a brand-new payment. That leaves the original
        # payment's own line orphaned (money already in hand, unmatched to
        # anything) — which then gets refunded back out via a fresh outbound
        # payment reconciled against that orphaned line.
        #
        # The unreconcile + post + reconcile + verify sequence is wrapped in a
        # SINGLE savepoint so it's all-or-nothing: if anything doesn't behave
        # the way a normal Odoo accounting setup would (unexpected reconciliation
        # shape, missing method on this Odoo version, etc.), the entire attempt
        # rolls back together — including the unreconcile step — leaving the
        # invoice exactly as it was (still reconciled/paid with its original
        # payment) instead of half-broken, and we fall through to the
        # already-proven-safe path below.
        orphaned_payment_lines = request.env['account.move.line']
        native_reversal_done = False
        if ratio >= 1.0 and inv.payment_state == 'paid':
            try:
                with request.env.cr.savepoint():
                    inv_ar_lines = inv.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable' and l.reconciled
                    )
                    if not inv_ar_lines:
                        raise ValueError('no reconciled receivable line found on invoice')

                    full_recs = inv_ar_lines.full_reconcile_id
                    group = full_recs.reconciled_line_ids if full_recs else inv_ar_lines
                    candidate_orphans = group - inv_ar_lines
                    group.remove_move_reconcile()

                    refund.action_post()
                    inv.invalidate_recordset()
                    if inv.payment_state != 'reversed':
                        # action_post()'s own auto-reconcile didn't catch it —
                        # finish the job manually against the now-open invoice line.
                        credit_ar = refund.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                        )
                        inv_ar_open = inv.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                        )
                        if credit_ar and inv_ar_open:
                            (credit_ar | inv_ar_open).reconcile()
                        inv.invalidate_recordset()
                    if inv.payment_state != 'reversed':
                        raise ValueError('native reversal did not settle as expected')

                    orphaned_payment_lines = candidate_orphans
                    native_reversal_done = True
            except Exception:
                orphaned_payment_lines = request.env['account.move.line']
                native_reversal_done = False
                refund.invalidate_recordset()

        if not native_reversal_done and refund.state != 'posted':
            refund.action_post()

        # ── give the cash back ──────────────────────────────────────────────
        # Two different situations end up here:
        #  - Native reversal succeeded: the credit note is already fully spent
        #    reconciling with the invoice, so refund.amount_residual is 0 — the
        #    money to hand back is sitting on the now-orphaned original payment
        #    line instead, refunded via a fresh outbound payment reconciled
        #    against THAT.
        #  - Native reversal wasn't attempted/didn't hold: falls back to the
        #    original behavior — register a payment directly against the
        #    credit note itself (its own amount_residual).
        if method == 'cash' and native_reversal_done and orphaned_payment_lines:
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
                refund_payment = request.env['account.payment'].sudo().create({
                    'payment_type': 'outbound',
                    'partner_type': 'customer',
                    'partner_id':   inv.partner_id.id,
                    'amount':       amount,
                    'journal_id':   cash_journal.id,
                    'date':         today,
                    'memo':         reason or f'استرداد نقدي من {inv.name}',
                })
                refund_payment.action_post()
                new_pay_ar = refund_payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                )
                open_orphans = orphaned_payment_lines.filtered(lambda l: not l.reconciled)
                if new_pay_ar and open_orphans:
                    (new_pay_ar | open_orphans).reconcile()
        elif method == 'cash' and refund.amount_residual:
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
