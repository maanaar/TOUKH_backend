# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    x_payment_type = fields.Selection([
        ('insurance', 'تامين صحي'),
        ('companies', 'شركات'),
        ('state',     'نفقة دوله'),
        ('takaful',   'تكافل و كرامه'),
    ], string='Payment Type')
