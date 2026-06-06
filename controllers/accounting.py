# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils import _json

# Journals to always exclude from the accounting dashboard
# (Miscellaneous, Cash-Basis, Exchange-Diff, Inventory-Valuation, etc.)
MISC_JOURNAL_TYPES = ('general',)


def _move_dict(move):
    lines = []
    for ml in move.line_ids:
        if ml.display_type in ('line_section', 'line_note'):
            continue
        lines.append({
            'id':           ml.id,
            'account_id':   ml.account_id.id   if ml.account_id else None,
            'account_code': ml.account_id.code if ml.account_id else '',
            'account_name': ml.account_id.name if ml.account_id else '',
            'name':         ml.name or '',
            'debit':        ml.debit,
            'credit':       ml.credit,
            'balance':      ml.balance,
        })
    return {
        'id':            move.id,
        'name':          move.name or '/',
        'ref':           move.ref  or '',
        'date':          str(move.date) if move.date else None,
        'state':         move.state,
        'move_type':     move.move_type,
        'journal_id':    move.journal_id.id   if move.journal_id else None,
        'journal_name':  move.journal_id.name if move.journal_id else '',
        'journal_code':  move.journal_id.code if move.journal_id else '',
        'journal_type':  move.journal_id.type if move.journal_id else '',
        'partner_name':  move.partner_id.name if move.partner_id else '',
        'narration':     move.narration or '',
        'amount_total':  move.amount_total,
        'total_debit':   sum(l['debit']  for l in lines),
        'total_credit':  sum(l['credit'] for l in lines),
        'balance':       sum(l['debit']  for l in lines) - sum(l['credit'] for l in lines),
        'lines':         lines,
    }


class AccountingDashboardController(http.Controller):

    # ── list journal entries ──────────────────────────────────────────────────
    @http.route('/saycare/api/accounting/journal-entries', type='http', auth='user', methods=['GET'], csrf=False)
    def list_entries(self, date_from='', date_to='', journal_id='', limit='200', **kw):
        """
        Returns all moves from non-general journals (invoices + manual entries).
        Excludes Miscellaneous Operations and other general-ledger system journals.
        """
        domain = [
            ('journal_id.type', 'not in', list(MISC_JOURNAL_TYPES)),
            ('move_type', 'in', ['entry', 'out_invoice', 'in_invoice', 'out_refund', 'in_refund']),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if journal_id:
            try:
                domain.append(('journal_id', '=', int(journal_id)))
            except ValueError:
                pass

        records = request.env['account.move'].sudo().search(
            domain, order='date desc, id desc', limit=int(limit)
        )
        return _json([_move_dict(m) for m in records])

    # ── single journal entry ──────────────────────────────────────────────────
    @http.route('/saycare/api/accounting/journal-entries/<int:move_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_entry(self, move_id, **kw):
        move = request.env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return _json({'error': 'not found'}, 404)
        return _json(_move_dict(move))

    # ── create journal entry ──────────────────────────────────────────────────
    @http.route('/saycare/api/accounting/journal-entries', type='http', auth='user', methods=['POST'], csrf=False)
    def create_entry(self, **kw):
        """
        Body: {
          date, journal_id, ref, narration,
          lines: [{ account_id, name, debit, credit }]
        }
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _json({'error': 'invalid JSON'}, 400)

        journal_id = body.get('journal_id')
        date       = body.get('date')
        lines_raw  = body.get('lines', [])

        if not journal_id:
            return _json({'error': 'journal_id is required'}, 400)
        if not lines_raw:
            return _json({'error': 'lines are required'}, 400)

        journal = request.env['account.journal'].sudo().browse(int(journal_id))
        if not journal.exists():
            return _json({'error': 'journal not found'}, 404)

        line_vals = []
        for line in lines_raw:
            account_id = line.get('account_id')
            if not account_id:
                continue
            line_vals.append((0, 0, {
                'account_id': int(account_id),
                'name':       line.get('name', ''),
                'debit':      float(line.get('debit', 0)),
                'credit':     float(line.get('credit', 0)),
            }))

        if not line_vals:
            return _json({'error': 'no valid lines provided'}, 400)

        move = request.env['account.move'].sudo().create({
            'move_type':  'entry',
            'journal_id': journal.id,
            'date':       date or None,
            'ref':        body.get('ref', ''),
            'narration':  body.get('narration', ''),
            'line_ids':   line_vals,
        })
        return _json(_move_dict(move), 201)

    # ── post (confirm) journal entry ──────────────────────────────────────────
    @http.route('/saycare/api/accounting/journal-entries/<int:move_id>/post', type='http', auth='user', methods=['POST'], csrf=False)
    def post_entry(self, move_id, **kw):
        move = request.env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return _json({'error': 'not found'}, 404)
        if move.state == 'draft':
            move.action_post()
        return _json(_move_dict(move))

    # ── balance summary per journal ───────────────────────────────────────────
    @http.route('/saycare/api/accounting/journal-balances', type='http', auth='user', methods=['GET'], csrf=False)
    def journal_balances(self, date_from='', date_to='', **kw):
        """
        Returns a balance summary for each non-general journal.
        Only includes posted entries.
        """
        domain = [
            ('move_type', 'in', ['entry', 'out_invoice', 'in_invoice', 'out_refund', 'in_refund']),
            ('state',     '=', 'posted'),
            ('journal_id.type', 'not in', list(MISC_JOURNAL_TYPES)),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        moves = request.env['account.move'].sudo().search(domain)

        # Group by journal
        journal_map = {}
        for move in moves:
            j = move.journal_id
            if j.id not in journal_map:
                journal_map[j.id] = {
                    'journal_id':   j.id,
                    'journal_name': j.name,
                    'journal_code': j.code,
                    'journal_type': j.type,
                    'total_debit':  0.0,
                    'total_credit': 0.0,
                    'entry_count':  0,
                }
            for ml in move.line_ids:
                if ml.display_type not in ('line_section', 'line_note'):
                    journal_map[j.id]['total_debit']  += ml.debit
                    journal_map[j.id]['total_credit']  += ml.credit
            journal_map[j.id]['entry_count'] += 1

        result = list(journal_map.values())
        for r in result:
            r['balance'] = r['total_debit'] - r['total_credit']

        return _json(sorted(result, key=lambda x: x['journal_name']))

    # ── list journals (non-general only, for dropdowns) ───────────────────────
    @http.route('/saycare/api/accounting/journals', type='http', auth='user', methods=['GET'], csrf=False)
    def list_journals(self, **kw):
        journals = request.env['account.journal'].sudo().search([
            ('type', 'not in', list(MISC_JOURNAL_TYPES)),
            ('active', '=', True),
        ], order='name')
        return _json([{
            'id':   j.id,
            'name': j.name,
            'code': j.code,
            'type': j.type,
        } for j in journals])

    # ── chart of accounts (for line account dropdowns) ────────────────────────
    @http.route('/saycare/api/accounting/accounts', type='http', auth='user', methods=['GET'], csrf=False)
    def list_accounts(self, **kw):
        accounts = request.env['account.account'].sudo().search(
            [('deprecated', '=', False)], order='code', limit=500
        )
        return _json([{
            'id':   a.id,
            'code': a.code,
            'name': a.name,
        } for a in accounts])
