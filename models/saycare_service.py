# -*- coding: utf-8 -*-
from odoo import models, fields, api


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

    basket_table_id = fields.One2many('basket.model','prod_id')
    basket_service_id = fields.Many2one('product.template',string='Service')

    def get_service_basket(self):
        for rec in self:
            rec.basket_table_id = [(5, 0, 0)]
            dats = []
            if rec.basket_service_id:
                for x in rec.basket_service_id.basket_table_id:
                    dats.append((0, 0, {'serial_no': x.serial_no,
                                        'product_product_id': x.product_product_id.id,
                                        'uom_id': x.uom_id.id,
                                        'planned_qty': x.planned_qty,
                                        'barcode': x.barcode,
                                        'price': x.price,
                                        'total_price': x.total_price,
                                        }
                                 ))
                rec.basket_table_id = dats



class BasketModel(models.Model):
    _name = 'basket.model'

    serial_no = fields.Integer(string="Serial No.")
    prod_id = fields.Many2one('product.template',string="Product")
    product_product_id = fields.Many2one('product.product',string="Product")
    uom_id = fields.Many2one('uom.uom',string="UOM")
    barcode = fields.Char(string="Barcode")
    planned_qty = fields.Float(string="Planned QTY")
    price = fields.Float(string="Price")
    total_price = fields.Float(string="Total Price",compute="compute_total_price",store=True)


    @api.depends('planned_qty', 'price')
    def compute_total_price(self):
        for rec in self:
            rec.total_price = rec.planned_qty * rec.price