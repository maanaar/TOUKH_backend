# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Remove the stale res.partner.x_payment_type field metadata.

    The field was dropped from partner_ext.py, but a leftover
    ir.model.fields row (registered as Char rather than Selection)
    was crashing the end-of-upgrade cleanup in ir.model.data._process_end,
    which expects the current field's `.ondelete` attribute while
    unlinking the old field's selection options.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    field = env['ir.model.fields'].search([
        ('model', '=', 'res.partner'),
        ('name', '=', 'x_payment_type'),
    ])
    field.unlink()
