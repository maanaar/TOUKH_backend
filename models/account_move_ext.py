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
class InsuranceCompany(models.Model):
    _inherit = 'insurance.company'

    provider_type = fields.Selection([
        ('cash', 'نقدي'),
        ('state', 'نفقة الدولة'),
        ('insurance', 'تأمين صحى'),
        ('takaful', 'تكافل وكرامة'),
        ('contracts', 'تعاقدات '),
        ('consult', 'مشورة'),
    ], string='provider Type')

