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

        if inv.state == 'draft':
            inv.action_post()

        amount = float(body.get('amount') or inv.amount_residual)
        if amount <= 0:
            amount = inv.amount_residual

        cash_journal = request.env['account.journal'].sudo().search([
            ('type', '=', 'cash'), ('company_id', '=', inv.company_id.id),
        ], limit=1)
        if not cash_journal:
            cash_journal = request.env['account.journal'].sudo().search([
                ('type', 'in', ['bank', 'cash']), ('company_id', '=', inv.company_id.id),
            ], limit=1)
        if not cash_journal:
            return _json({'error': 'no cash/bank journal found'}, 400)

        # Find the AR line on the invoice (must have a residual amount)
        inv_ar_line = inv.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
                      and not l.reconciled
        )[:1]
        if not inv_ar_line:
            # Already paid — nothing to do
            inv.invalidate_recordset()
            return _json({'ok': True, 'payment_state': inv.payment_state,
                          'amount_residual': inv.amount_residual, 'invoice': _invoice_dict(inv)})

        cash_account = cash_journal.default_account_id
        if not cash_account:
            return _json({'error': 'cash journal has no default account'}, 400)

        # Direct payment entry: Cash (Dr) / AR (Cr)
        # Bypasses the outstanding-receipts transit account → invoice becomes paid immediately
        payment_move = request.env['account.move'].sudo().create({
            'move_type':  'entry',
            'journal_id': cash_journal.id,
            'date':       fields.Date.today(),
            'ref':        inv.name or '',
            'line_ids': [
                (0, 0, {
                    'account_id': cash_account.id,
                    'debit':      amount,
                    'credit':     0,
                    'partner_id': inv.partner_id.id if inv.partner_id else False,
                    'name':       inv.name or '',
                }),
                (0, 0, {
                    'account_id': inv_ar_line.account_id.id,
                    'debit':      0,
                    'credit':     amount,
                    'partner_id': inv.partner_id.id if inv.partner_id else False,
                    'name':       inv.name or '',
                }),
            ],
        })
        payment_move.action_post()

        # Reconcile the two AR lines → invoice.payment_state becomes 'paid'
        ar_lines = (inv.line_ids | payment_move.line_ids).filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        if ar_lines:
            ar_lines.reconcile()

        inv.invalidate_recordset()
        return _json({
            'ok':              True,
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
