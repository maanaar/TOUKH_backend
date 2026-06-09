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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name  = self.product_id.name
        self.price = self.product_id.list_price
        if self.product_id.default_code:
            self.code = self.product_id.default_code
        # Assign specialty's category to the product if not already set
        if self.specialty_id and self.specialty_id.categ_id:
            if not self.product_id.categ_id or self.product_id.categ_id != self.specialty_id.categ_id:
                self.product_id.categ_id = self.specialty_id.categ_id
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

    def _auto_create_clinic_service(self):
        """If this product's category matches any specialty's categ_id,
        create a saycare.service for it (if one doesn't already exist)."""
        Service   = self.env['saycare.service'].sudo()
        Specialty = self.env['saycare.specialty'].sudo()
        for product in self:
            if not product.categ_id:
                continue
            specialties = Specialty.search([('categ_id', '=', product.categ_id.id)])
            for specialty in specialties:
                already = Service.search([
                    ('product_id', '=', product.id),
                    ('specialty_id', '=', specialty.id),
                ], limit=1)
                if not already:
                    Service.create({
                        'name':         product.name,
                        'price':        product.list_price,
                        'code':         product.default_code or '',
                        'specialty_id': specialty.id,
                        'product_id':   product.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._auto_create_clinic_service()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'categ_id' in vals or 'name' in vals or 'list_price' in vals:
            self._auto_create_clinic_service()
            # Sync name/price changes to existing service records
            if 'name' in vals or 'list_price' in vals:
                Service = self.env['saycare.service'].sudo()
                for product in self:
                    services = Service.search([('product_id', '=', product.id)])
                    update = {}
                    if 'name' in vals:
                        update['name'] = product.name
                    if 'list_price' in vals:
                        update['price'] = product.list_price
                    if update:
                        services.write(update)
        return res

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