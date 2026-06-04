# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    financial_class = fields.Selection(
        related='partner_id.financial_class',
        string='الوجهة المالية',
        store=True,
        readonly=True,
    )


