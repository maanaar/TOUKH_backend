# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    financial_class = fields.Selection([
        ('cash',         'نقدي'),
        ('state',        'نفقة الدولة'),
        ('consultation', 'مشورة'),
        ('takaful',      'تكافل وكرامة'),
        ('insurance',    'تأمين صحى'),
        ('contract',     'تعاقدات'),
        ('moh',          'وزارة الصحة'),
        ('staff',        'عاملين'),
    ], string='الوجهة المالية')
