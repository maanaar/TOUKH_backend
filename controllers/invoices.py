# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from .utils import _json


def _invoice_dict(inv):
    return {
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
        'narration':    inv.narration or '',
        'lines': [{
            'id':          line.id,
            'name':        line.name or '',
            'quantity':    line.quantity,
            'price_unit':  line.price_unit,
            'price_total': line.price_total,
        } for line in inv.invoice_line_ids if line.display_type in ('product', False, '')],
        'odoo_url': f'/odoo/accounting/customer-invoices/{inv.id}',
    }


class InvoiceController(http.Controller):

    @http.route('/saycare/api/invoice/<int:invoice_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, invoice_id, **kw):
        inv = request.env['account.move'].sudo().browse(invoice_id)
        if not inv.exists() or inv.move_type != 'out_invoice':
            return _json({'error': 'invoice not found'}, 404)
        return _json(_invoice_dict(inv))

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
                return _json({'ok': True, 'payment_id': payment.id if payment else None,
                              'payment_state': 'paid', 'amount_residual': 0,
                              'invoice': _invoice_dict(inv)})

            amount = float(body.get('amount') or 0) or inv.amount_residual

            # Step 2: journal from visit.payment_method
            # 'cash' (نقدي) → cash journal  |  'deferred' (فيزا) → bank journal
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

        new_lines = []
        for line in body.get('lines', []):
            name  = (line.get('name') or '').strip()
            price = float(line.get('price') or 0)
            qty   = float(line.get('qty')   or 1)
            if not name or price <= 0:
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

        if new_lines:
            was_posted = inv.state == 'posted'
            if was_posted:
                inv.button_draft()
            inv.write({'invoice_line_ids': new_lines})
            if was_posted:
                inv.action_post()

        return _json(_invoice_dict(inv))

    @http.route('/saycare/api/invoices', type='http', auth='user', methods=['GET'], csrf=False)
    def get_list(self, partner_id='', state='', payment_state='', **kw):
        domain = [('move_type', '=', 'out_invoice')]
        if partner_id:
            domain.append(('partner_id', '=', int(partner_id)))
        if state:
            domain.append(('state', '=', state))
        if payment_state:
            domain.append(('payment_state', '=', payment_state))
        records = request.env['account.move'].sudo().search(
            domain, order='invoice_date desc, id desc', limit=100
        )
        return _json([_invoice_dict(i) for i in records])
