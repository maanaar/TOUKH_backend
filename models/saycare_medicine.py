# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareUsageType(models.Model):
    _name        = 'saycare.usage.type'
    _description = 'Usage Type'
    _order       = 'name'

    name = fields.Char(string='نوع الاستخدام', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Usage type name must be unique.'),
    ]


class ProductCategoryMedicine(models.Model):
    _inherit = 'product.category'

    is_medicines = fields.Boolean(string='أدوية', default=False)

    medicine_product_count = fields.Integer(
        string='عدد الأصناف',
        compute='_compute_medicine_product_count',
    )

    @api.depends('is_medicines')
    def _compute_medicine_product_count(self):
        Product = self.env['product.template'].sudo()
        for rec in self:
            if rec.is_medicines:
                rec.medicine_product_count = Product.search_count([
                    ('categ_id', 'child_of', rec.id),
                    ('active', '=', True),
                ])
            else:
                rec.medicine_product_count = 0

    def action_view_pharmacy_products(self):
        self.ensure_one()
        return {
            'name':      f'أصناف {self.name}',
            'type':      'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain':    [('categ_id', 'child_of', self.id)],
            'context':   {'default_categ_id': self.id},
        }


class ProductTemplateMedicine(models.Model):
    _inherit = 'product.template'

    # ── 1.1  المجموعة ─────────────────────────────────────────────────────────
    group_id = fields.Many2one(
        'product.category',
        string='المجموعة',
    )

    # ── 1.2  نوع الاستخدام (Many2many) ─────────────────────────────────────────
    usage_type_ids = fields.Many2many(
        'saycare.usage.type',
        'product_tmpl_usage_type_rel',
        'product_tmpl_id',
        'usage_type_id',
        string='نوع الاستخدام',
    )

    # ── 2.1  الوحدة الصغرى linked to UOM ───────────────────────────────────────
    uom_small = fields.Many2one(
        'uom.uom',
        string='الوحدة الصغرى',
    )

    # ── 3.1 / 3.2  السعر الجبرى — EGP ─────────────────────────────────────────
    forced_price = fields.Monetary(
        string='السعر الجبرى',
        currency_field='forced_price_currency_id',
    )
    forced_price_currency_id = fields.Many2one(
        'res.currency',
        string='عملة السعر الجبرى',
        default=lambda self: self.env['res.currency'].search(
            [('name', '=', 'EGP')], limit=1
        ),
    )

    # ── 4.1  يحتاج الى تبريد + درجة الحرارة ────────────────────────────────────
    needs_refrigeration = fields.Boolean(string='يحتاج الى تبريد')
    storage_temp        = fields.Float(
        string='درجة الحرارة (°C)',
        digits=(5, 1),
    )

    # ── 5  متشابهات ─────────────────────────────────────────────────────────────
    similarity_type = fields.Selection([
        ('look_alike',         'متشابه فى الشكل'),
        ('sound_alike',        'متشابه فى النطق'),
        ('high_concentration', 'عالى التركيز'),
        ('hazardous',          'مادة خطرة'),
    ], string='متشابهات')

    # ── بيانات الدواء — طريقة الإعطاء الثانوية ──────────────────────────────────
    secondary_route = fields.Selection([
        ('oral',        'فموي'),
        ('iv',          'وريدي'),
        ('im',          'عضلي'),
        ('sc',          'تحت الجلد'),
        ('topical',     'موضعي'),
        ('inhalation',  'استنشاق'),
        ('sublingual',  'تحت اللسان'),
        ('rectal',      'مستقيمي'),
        ('ophthalmic',  'عيني'),
        ('otic',        'أذني'),
        ('nasal',       'أنفي'),
        ('transdermal', 'عبر الجلد'),
    ], string='طريقة الإعطاء الثانوية')


# ─────────────────────────────────────────────────────────────────────────────
#  stock.move — Q Sant (كمية المرسلة)
# ─────────────────────────────────────────────────────────────────────────────
class StockMoveQSant(models.Model):
    _inherit = 'stock.move'

    q_sant = fields.Float(
        string='Q Sant',
        digits='Product Unit of Measure',
        default=0.0,
        help='Quantity sent (filled by sender after confirmation)',
    )
