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
    is_look_alike         = fields.Boolean(string='متشابه في الشكل')
    is_sound_alike        = fields.Boolean(string='متشابه في النطق')
    is_high_concentration = fields.Boolean(string='عالي التركيز')
    is_hazardous          = fields.Boolean(string='مادة خطرة')

    # ── 6  المعلومات الدوائية ──────────────────────────────────────────────────
    generic_name = fields.Char(string='المادة الفعالة (Generic Name)')
    dosage_form  = fields.Selection([
        ('tablet',      'أقراص'),
        ('capsule',     'كبسولات'),
        ('syrup',       'شراب'),
        ('suspension',  'معلق'),
        ('injection',   'حقن'),
        ('ointment',    'مرهم'),
        ('cream',       'كريم'),
        ('gel',         'جل'),
        ('drops',       'قطرة'),
        ('spray',       'بخاخ'),
        ('suppository', 'تحاميل/لبوس'),
        ('inhaler',     'مستنشق'),
        ('powder',      'بودرة'),
    ], string='الشكل الصيدلاني')
    medicine_concentration = fields.Char(string='التركيز / الجرعة')
    
    primary_route = fields.Selection([
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
    ], string='طريقة الإعطاء الأساسية')

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

    atc_code            = fields.Char(string='الفئة الدوائية (ATC Code)')
    dispensing_category = fields.Selection([
        ('rx',         'بوصفة طبية (Rx)'),
        ('otc',        'بدون وصفة طبية (OTC)'),
        ('controlled', 'جدول / خاضع للرقابة (Controlled)'),
    ], string='تصنيف الصرف')
    usual_dose     = fields.Char(string='الجرعة المعتادة')
    max_daily_dose = fields.Char(string='الحد الأقصى للجرعة اليومية')

    # ── 7  الاستخدام في الحمل والرضاعة ─────────────────────────────────────────
    pregnancy_category = fields.Selection([
        ('a', 'تصنيف A'),
        ('b', 'تصنيف B'),
        ('c', 'تصنيف C'),
        ('d', 'تصنيف D'),
        ('x', 'تصنيف X'),
    ], string='تصنيف الحمل (FDA)')
    lactation_use = fields.Selection([
        ('safe',            'آمن'),
        ('caution',         'يستخدم بحذر'),
        ('unsafe',          'غير آمن / تجنبه'),
        ('contraindicated', 'موانع استخدام مطلقة'),
    ], string='الاستخدام أثناء الرضاعة')
    pediatric_use = fields.Selection([
        ('safe',            'آمن'),
        ('caution',         'يستخدم بحذر'),
        ('unsafe',          'غير آمن / تجنبه'),
        ('contraindicated', 'موانع استخدام مطلقة'),
    ], string='الاستخدام في الأطفال')

    # ── 8  التحذيرات والتفاعلات ───────────────────────────────────────────────
    contraindications = fields.Text(string='موانع الاستخدام')
    special_warnings  = fields.Text(string='التحذيرات الخاصة')
    side_effects      = fields.Text(string='الآثار الجانبية الشائعة')
    drug_interactions = fields.Text(string='التفاعلات الدوائية')


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


# ─────────────────────────────────────────────────────────────────────────────
#  stock.picking — extend native state with SayCare "معتمد" step
#  Workflow: assigned → quantities_confirmed → done
# ─────────────────────────────────────────────────────────────────────────────
class StockPickingScState(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(
        selection_add=[('quantities_confirmed', 'Confirmed'), ('done',)],
        ondelete={'quantities_confirmed': lambda recs: recs.write({'state': 'assigned'})},
    )
