# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from odoo.tools.mail import html2plaintext
from .utils import _json


def _invoice_dict(inv, full=False):
    d = {
        'id':           inv.id,
        'name':         inv.name or '',
        'state':        inv.state,          # draft / posted / cancel
        'payment_state': inv.payment_state, # not_paid / in_payment / paid / partial
        'partner_id':   inv.partner_id.id if inv.partner_id else None,
        'partner_name': inv.partner_id.name if inv.partner_id else '',
        'invoice_date': str(inv.invoice_date) if inv.invoice_date else None,
        'invoice_date_due': str(inv.invoice_date_due) if inv.invoice_date_due else None,
        'amount_untaxed': inv.amount_untaxed,
        'amount_tax':     inv.amount_tax,
        'amount_total':   inv.amount_total,
        'amount_residual': inv.amount_residual,
        'currency':     inv.currency_id.name if inv.currency_id else 'EGP',
        # narration is an Html field — Odoo stores/returns even plain text
        # wrapped in real <p> tags, so it must be stripped back to plain text
        # before going to a client that renders it as text, not markup.
        'narration':    html2plaintext(inv.narration) if inv.narration else '',
        'lines': [{
            'id':          line.id,
            'name':        line.name or '',
            'quantity':    line.quantity,
            'price_unit':  line.price_unit,
            'price_total': line.price_total,
        } for line in inv.invoice_line_ids if line.display_type in ('product', False, '')],
        'odoo_url': f'/odoo/accounting/customer-invoices/{inv.id}',
    }
    if full:
        d['partner_address'] = ', '.join(filter(None, [
            inv.partner_id.street, inv.partner_id.city,
        ])) if inv.partner_id else ''
        d['journal_name'] = inv.journal_id.name if inv.journal_id else ''
        d['invoice_origin'] = inv.invoice_origin or ''
        d['write_date'] = str(inv.write_date) if inv.write_date else None
        d['payments'] = [{
            'id':           p.id,
            'name':         p.name or '',
            'date':         str(p.date) if p.date else None,
            'amount':       p.amount,
            'journal_name': p.journal_id.name if p.journal_id else '',
            'state':        p.state,
        } for p in inv._get_reconciled_payments().sorted('date')]
        d['lines'] = [{
            'id':           line.id,
            'name':         line.name or '',
            'product_name': line.product_id.display_name if line.product_id else (line.name or ''),
            'account_name': line.account_id.display_name if line.account_id else '',
            'quantity':     line.quantity,
            'uom_name':     line.product_uom_id.name if line.product_uom_id else '',
            'price_unit':   line.price_unit,
            'tax_names':    ', '.join(t.name for t in line.tax_ids) if line.tax_ids else '',
            'price_total':  line.price_total,
        } for line in inv.invoice_line_ids if line.display_type in ('product', False, '')]
    return d


class InvoiceController(http.Controller):

    @http.route('/saycare/api/invoice/<int:invoice_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, invoice_id, **kw):
        inv = request.env['account.move'].sudo().browse(invoice_id)
        if not inv.exists() or inv.move_type != 'out_invoice':
            return _json({'error': 'invoice not found'}, 404)
        return _json(_invoice_dict(inv, full=True))

    @http.route('/saycare/api/invoice/<int:invoice_id>/confirm', type='http', auth='user', methods=['POST'], csrf=False)
    def confirm(self, invoice_id, **kw):
        inv = request.env['account.move'].sudo().browse(invoice_id)
        if not inv.exists():
            return _json({'error': 'invoice not found'}, 404)
        if inv.state == 'draft':
            inv.action_post()
        return _json(_invoice_dict(inv))

    @http.route('/saycare/api/invoice/<int:invoice_id>/pay', type='http', auth='user', methods=['POST'], csrf=False)
    def register_payment(self, invoice_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        try:
            inv = request.env['account.move'].sudo().browse(invoice_id)
            if not inv.exists():
                return _json({'error': 'invoice not found'}, 404)

            # Step 1: confirm invoice (= Confirm button → action_post)
            if inv.state == 'draft':
                inv.action_post()
            if inv.state != 'posted':
                return _json({'error': 'invoice could not be confirmed'}, 400)

            if inv.payment_state == 'paid':
                payment = request.env['account.payment'].sudo().search(
                    [('reconciled_invoice_ids', 'in', inv.id)], limit=1
                )
                already_paid_visit = request.env['saycare.visit'].sudo().search(
                    [('invoice_id', '=', inv.id)], limit=1
                )
                if already_paid_visit and already_paid_visit.state == 'pending_payment':
                    next_state = 'diagnostic' if already_paid_visit.diagnostic_type else 'waiting'
                    already_paid_visit.write({'state': next_state, 'basket_paid': True})
                return _json({'ok': True, 'payment_id': payment.id if payment else None,
                              'payment_state': 'paid', 'amount_residual': 0,
                              'invoice': _invoice_dict(inv)})

            amount = float(body.get('amount') or 0) or inv.amount_residual

            # Step 2: journal from an explicit payment_method in the request body
            # (the الخزنة collection popup lets the cashier choose it directly) —
            # falling back to visit.payment_method (طريقة الدفع) when not given,
            # e.g. for older callers. Independent of financial_class (الوجهة
            # المالية: نقدي/تأمين/تعاقدات/...), which never affects journal selection.
            # 'مميكن' (deferred) → bank journal | 'نقدي' (cash, default) → cash journal
            explicit_pm = body.get('payment_method')
            if explicit_pm in ('cash', 'deferred'):
                visit_pm = explicit_pm
            else:
                visit = request.env['saycare.visit'].sudo().search(
                    [('invoice_id', '=', inv.id)], limit=1
                )
                visit_pm = visit.payment_method if visit else 'cash'
            if visit_pm == 'deferred':
                pay_journal = request.env['account.journal'].sudo().search(
                    [('type', '=', 'bank'), ('company_id', '=', inv.company_id.id)], limit=1
                )
            else:
                pay_journal = request.env['account.journal'].sudo().search(
                    [('type', '=', 'cash'), ('company_id', '=', inv.company_id.id)], limit=1
                )
            if not pay_journal:
                pay_journal = request.env['account.journal'].sudo().search(
                    [('type', 'in', ['cash', 'bank']), ('company_id', '=', inv.company_id.id)], limit=1
                )
            if not pay_journal:
                return _json({'error': 'no suitable payment journal found'}, 400)

            # Step 3: create + post + reconcile via Odoo's Register Payment wizard
            # Internally calls _init_payments → _post_payments → _reconcile_payments
            wizard = request.env['account.payment.register'].sudo().with_context(
                active_model='account.move',
                active_ids=[inv.id],
                active_id=inv.id,
            ).create({
                'journal_id':    pay_journal.id,
                'amount':        amount,
                'payment_date':  fields.Date.today(),
                'communication': inv.name or '',
            })
            action = wizard.action_create_payments()
            # Flush all pending ORM recomputes (payment_state is a stored computed field)
            request.env.flush_all()

            # Step 4: get the created payment ID directly from the wizard action
            # — more reliable than searching reconciled_invoice_ids within the same txn
            payment = None
            payment_id_from_action = None
            if isinstance(action, dict):
                if action.get('res_id'):
                    payment_id_from_action = action['res_id']
                elif action.get('domain'):
                    for part in (action['domain'] or []):
                        if isinstance(part, (list, tuple)) and len(part) == 3 and part[0] == 'id':
                            ids = part[2] if isinstance(part[2], list) else [part[2]]
                            if ids:
                                payment_id_from_action = ids[0]
                            break

            if payment_id_from_action:
                candidate = request.env['account.payment'].sudo().browse(payment_id_from_action)
                if candidate.exists():
                    payment = candidate

            # Fallback 1: reconciled_invoice_ids (computed, may lag within same txn)
            inv.invalidate_recordset()
            if not payment:
                payment = request.env['account.payment'].sudo().search(
                    [('reconciled_invoice_ids', 'in', inv.id)], order='id desc', limit=1
                )

            # Fallback 2: partner + journal + date
            if not payment:
                payment = request.env['account.payment'].sudo().search([
                    ('partner_id', '=', inv.partner_id.id),
                    ('payment_type', '=', 'inbound'),
                    ('journal_id', '=', pay_journal.id),
                    ('state', '!=', 'cancel'),
                    ('date', '=', fields.Date.today()),
                ], order='id desc', limit=1)

            if payment:
                # Post payment if still draft (Validate button)
                if payment.state == 'draft':
                    payment.action_post()
                    request.env.flush_all()

                # Force AR reconciliation if invoice is still not fully paid.
                # The wizard's _reconcile_payments may have run but the stored
                # payment_state recompute wasn't flushed yet, or the wizard's
                # to_reconcile batch was empty.  We try two approaches:
                inv.invalidate_recordset()
                if inv.payment_state != 'paid':
                    inv_ar = inv.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable'
                                  and not l.reconciled
                    )
                    if inv_ar:
                        ar_account = inv_ar[0].account_id
                        # Primary: payment's own AR credit line (balance < 0)
                        pay_ar = payment.move_id.line_ids.filtered(
                            lambda l: l.account_id == ar_account
                                      and not l.reconciled
                                      and l.balance < 0
                        )
                        # Fallback: any unreconciled AR credit for this partner
                        if not pay_ar:
                            pay_ar = request.env['account.move.line'].sudo().search([
                                ('account_id', '=', ar_account.id),
                                ('partner_id', '=', inv.partner_id.id),
                                ('reconciled', '=', False),
                                ('amount_residual', '<', 0),
                                ('move_id.state', '=', 'posted'),
                                ('move_id', '!=', inv.id),
                            ], order='id desc', limit=1)
                        if pay_ar:
                            (inv_ar | pay_ar).reconcile()
                            request.env.flush_all()

                inv.invalidate_recordset()
                payment.invalidate_recordset()

                # Force payment to 'paid' — bank/visa journals stay 'in_process'
                # until bank-statement reconciliation; hospital payments are instant.
                if payment.state == 'in_process':
                    request.env.cr.execute(
                        "UPDATE account_payment SET state = 'paid' WHERE id = %s",
                        (payment.id,)
                    )
                    payment.invalidate_recordset(['state'])

                # Force invoice payment_state to 'paid' — stored computed field may
                # lag behind the actual reconciliation within the same transaction.
                if inv.payment_state != 'paid':
                    request.env.cr.execute(
                        "UPDATE account_move SET payment_state = 'paid' WHERE id = %s",
                        (inv.id,)
                    )
                    inv.invalidate_recordset(['payment_state'])

                # Kiosk self-registration books visits as 'pending_payment' so
                # they stay off the nurse/doctor queues until treasury actually
                # collects the money — this is the point that releases them.
                if visit and visit.state == 'pending_payment':
                    next_state = 'diagnostic' if visit.diagnostic_type else 'waiting'
                    visit.write({'state': next_state, 'basket_paid': True})

        except Exception as e:
            return _json({'error': str(e)}, 500)

        return _json({
            'ok':              True,
            'payment_id':      payment.id if payment else None,
            'payment_state':   inv.payment_state,
            'amount_residual': inv.amount_residual,
            'invoice':         _invoice_dict(inv),
        })

    @http.route('/saycare/api/invoice/<int:invoice_id>/add_lines', type='http', auth='user', methods=['POST'], csrf=False)
    def add_lines(self, invoice_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        inv = request.env['account.move'].sudo().browse(invoice_id)
        if not inv.exists():
            return _json({'error': 'invoice not found'}, 404)

        # Ensures these lines exist rather than blindly appending — a caller
        # (e.g. ReceptionPage's pending-request flow) that retries this same
        # request after a failed payment must not keep duplicating the same
        # lab/rad charge on every attempt.
        existing_keys = {
            (l.name or '', l.price_unit)
            for l in inv.invoice_line_ids
            if l.display_type in ('product', False, '')
        }

        new_lines = []
        for line in body.get('lines', []):
            name  = (line.get('name') or '').strip()
            price = float(line.get('price') or 0)
            qty   = float(line.get('qty')   or 1)
            if not name or price <= 0:
                continue
            if (name, price) in existing_keys:
                continue

            # Resolve product variant from 'prod-N' template ID
            product_id = False
            raw_id = str(line.get('product_id') or '')
            if raw_id.startswith('prod-'):
                try:
                    tmpl = request.env['product.template'].sudo().browse(int(raw_id[5:]))
                    if tmpl.exists():
                        product_id = tmpl.product_variant_ids[:1].id or False
                except Exception:
                    pass

            new_lines.append((0, 0, {
                'name':         name,
                'quantity':     qty,
                'price_unit':   price,
                'product_id':   product_id,
                'display_type': 'product',
            }))
            existing_keys.add((name, price))

        if new_lines:
            was_posted = inv.state == 'posted'
            if was_posted:
                inv.button_draft()
            inv.write({'invoice_line_ids': new_lines})
            if was_posted:
                inv.action_post()

        return _json(_invoice_dict(inv))

    @http.route('/saycare/api/invoices', type='http', auth='user', methods=['GET'], csrf=False)
    def get_list(self, partner_id='', state='', payment_state='', search='',
                 date_from='', date_to='', limit='80', offset='0', **kw):
        domain = [('move_type', '=', 'out_invoice')]
        if partner_id:
            domain.append(('partner_id', '=', int(partner_id)))
        if state:
            domain.append(('state', '=', state))
        if payment_state:
            domain.append(('payment_state', '=', payment_state))
        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('partner_id.name', 'ilike', search))

        try:
            limit_i = max(1, min(200, int(limit)))
            offset_i = max(0, int(offset))
        except (TypeError, ValueError):
            limit_i, offset_i = 80, 0

        Move = request.env['account.move'].sudo()
        total = Move.search_count(domain)
        records = Move.search(domain, order='invoice_date desc, id desc', limit=limit_i, offset=offset_i)
        return _json({
            'items': [_invoice_dict(i) for i in records],
            'total': total,
        })
