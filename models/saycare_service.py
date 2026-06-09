# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareService(models.Model):
    _name        = 'saycare.service'
    _description = 'Medical Service / Price Catalog'
    _order       = 'specialty_id, name'

    product_id   = fields.Many2one(
        'product.template',
        string='المنتج',
        ondelete='set null',
    )
    name         = fields.Char(string='Service Name', required=True)
    code         = fields.Char(string='Service Code')
    specialty_id = fields.Many2one('saycare.specialty', string='Specialty')
    visit_type   = fields.Selection([
        ('outpatient',   'كشف'),
        ('inpatient',    'داخلي'),
        ('emergency',    'طوارئ'),
        ('consultation', 'استشارة'),
    ], string='نوع الزيارة')
    price        = fields.Float(string='Price (EGP)', default=0.0)
    insurance_price = fields.Float(string='Insurance Price (EGP)', default=0.0)
    active       = fields.Boolean(default=True)
    notes        = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Service code must be unique.'),
    ]

class ProductCategory(models.Model):
    _inherit = 'product.category'

    categ_type = fields.Selection([
        ('services',   'خدمات'),
        ('procedures', 'إجراءات'),
    ], string='Category Type')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_large = fields.Char(string='الوحدة الكبرى')
    uom_medium = fields.Char(string='الوحدة المتوسطة')
    uom_largee = fields.Many2one('uom.uom', string='الوحدة الكبرى')
    uom_mediumm = fields.Many2one('uom.uom', string='الوحدة المتوسطة')

    categ_type = fields.Selection(
        selection=[('services', 'خدمات'), ('procedures', 'إجراءات')],
        related='categ_id.categ_type',
        string='Category Type',
        readonly=True,
        store=False,
    )



