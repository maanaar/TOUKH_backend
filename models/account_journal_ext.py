# -*- coding: utf-8 -*-
from odoo import models, fields


# Canonical list — single source of truth used by model + controller
FINANCIAL_JOURNALS = [
    # (financial_class, name_ar, code)
    ('cash',         'نقدي',           'NQDI'),
    ('insurance',    'تأمين صحى',       'TMIN'),
    ('state',        'نفقة الدولة',     'NFQA'),
    ('takaful',      'تكافل وكرامة',    'TKFL'),
    ('consultation', 'مشورة',           'MSHR'),
    ('contract',     'تعاقدات',         'TAQD'),
    ('moh',          'وزارة الصحة',     'MWZR'),
    ('staff',        'عاملين',          'AMLN'),
]


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
