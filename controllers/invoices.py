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

        inv = request.env['account.move'].sudo().browse(invoice_id)
        if not inv.exists():
            return _json({'error': 'invoice not found'}, 404)

        # confirm first if still draft
        if inv.state == 'draft':
            inv.action_post()

        # Guard: already fully paid
        if inv.payment_state == 'paid':
            return _json({'error': 'invoice already paid'}, 400)

        amount = float(body.get('amount', inv.amount_residual))

        # Guard: zero or negative amount would create a dangling suspense entry
        if amount <= 0:
            return _json({'error': 'amount must be greater than zero'}, 400)

        # Guard: must have an open receivable line to reconcile against
        receivable_line = inv.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        if not receivable_line:
            return _json({'error': 'no open receivable line found on invoice'}, 400)

        cash_journal = request.env['account.journal'].sudo().search([
            ('type', '=', 'cash'),
            ('company_id', '=', inv.company_id.id),
        ], limit=1)
        if not cash_journal:
            cash_journal = request.env['account.journal'].sudo().search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', inv.company_id.id),
            ], limit=1)
        if not cash_journal:
            return _json({'error': 'no cash/bank journal found'}, 400)

        # Find or create an open bank statement for this journal to group the line
        statement = request.env['account.bank.statement'].sudo().search([
            ('journal_id', '=', cash_journal.id),
            ('state', '!=', 'confirm'),
        ], order='id desc', limit=1)
        if not statement:
            statement = request.env['account.bank.statement'].sudo().create({
                'journal_id': cash_journal.id,
                'name': str(fields.Date.today()),
            })

        st_line = request.env['account.bank.statement.line'].sudo().create({
            'statement_id': statement.id,
            'journal_id':   cash_journal.id,
            'date':         fields.Date.today(),
            'payment_ref':  f'{inv.name or ""} — {amount} {inv.currency_id.name or "EGP"}',
            'amount':       amount,
            'partner_id':   inv.partner_id.id if inv.partner_id else False,
        })

        # Post the underlying journal entry so it affects the journal balance
        if st_line.move_id and st_line.move_id.state != 'posted':
            st_line.move_id.action_post()

        # Reconcile immediately — clears suspense entry, updates balance, marks invoice paid
        st_line.reconcile([{'id': receivable_line[0].id}])

        inv.invalidate_recordset()
        return _json({
            'ok':            True,
            'payment_state': inv.payment_state,
            'amount_residual': inv.amount_residual,
            'invoice':       _invoice_dict(inv),
        })

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
