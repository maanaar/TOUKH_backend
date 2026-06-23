# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    x_payment_type = fields.Selection([
        ('cash', 'نقدي'),
        ('state', 'نفقة الدولة'),
        ('insurance', 'تأمين صحى'),
        ('takaful', 'تكافل وكرامة'),
        ('contracts', 'تعاقدات'),
        ('consult', 'مشورة'),
    ], string='Payment Type')
