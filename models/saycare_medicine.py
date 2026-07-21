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

    # ── 9  التصنيف (شاشة الأصناف — عام) ────────────────────────────────────────
    name_en        = fields.Char(string='english name')
    main_category  = fields.Selection([
        ('drugs',       'أدوية'),
        ('consumables', 'مستلزمات'),
        ('solutions',   'محاليل'),
        ('devices',     'أجهزة'),
    ], string='التصنيف الرئيسي')
    sub_category   = fields.Selection([
        ('cold',        'أدوية البرد والأنفلونزا'),
        ('pain',        'مسكنات الألم'),
        ('antibiotics', 'مضادات حيوية'),
        ('cardiac',     'قلب وأوعية'),
    ], string='التصنيف الفرعي')
    use_types      = fields.Char(string='نوع الاستخدام (شاشة الأصناف)',
                                  help='قيم مفصولة بفاصلة: pharmacy, ward, lab, radiology')
    department     = fields.Char(string='القسم المسؤول')
    is_critical    = fields.Boolean(string='صنف حرج')
    needs_approval = fields.Boolean(string='يحتاج موافقة خاصة')

    # ── 10  خصائص الصنف ────────────────────────────────────────────────────────
    can_dispense           = fields.Boolean(string='قابل للصرف', default=True)
    show_pharmacy          = fields.Boolean(string='يظهر في الصيدلية')
    show_warehouse         = fields.Boolean(string='يظهر في المخزن')
    show_purchase_req      = fields.Boolean(string='يظهر في طلبات الشراء')
    show_internal_transfer = fields.Boolean(string='يظهر في طلبات الصرف الداخلي')
    needs_tracking         = fields.Boolean(string='يحتاج تتبع')
    has_expiry             = fields.Boolean(string='له تاريخ صلاحية')
    allow_fractions        = fields.Boolean(string='يسمح بالكسر')
    allow_partial          = fields.Boolean(string='يسمح بالصرف الجزئي')

    # ── 11  الأسعار ────────────────────────────────────────────────────────────
    tax_purchase     = fields.Char(string='ضريبة الشراء')
    tax_sale         = fields.Char(string='ضريبة البيع')
    currency         = fields.Char(string='العملة (شاشة الأصناف)')
    price_include_tax = fields.Boolean(string='السعر شامل الضريبة')

    # ── 12  الشركة والمورد ─────────────────────────────────────────────────────
    manufacturer     = fields.Many2one('res.partner', string='الشركة المصنعة')
    origin_country   = fields.Char(string='بلد المنشأ')
    purchase_policy  = fields.Selection([
        ('on_order', 'شراء عند الطلب'),
        ('on_stock', 'الحفاظ على المخزون'),
    ], string='سياسة الشراء')
    min_purchase_qty = fields.Integer(string='أقل كمية شراء')

    # ── 13  المخزون والتخزين (شاشة الأصناف) ────────────────────────────────────
    default_warehouse = fields.Char(string='المخزن الافتراضي')
    storage_location  = fields.Char(string='موقع التخزين')
    bin_location      = fields.Char(string='Bin / Shelf / Rack')
    dispense_method   = fields.Selection([
        ('fefo', 'FEFO (الأقرب صلاحية)'),
        ('fifo', 'FIFO (الأقدم أولاً)'),
        ('lifo', 'LIFO'),
    ], string='طريقة الصرف')
    reorder_point  = fields.Integer(string='حد إعادة الطلب')
    safety_stock   = fields.Integer(string='حد الأمان')
    min_qty        = fields.Integer(string='الكمية الدنيا')
    max_qty        = fields.Integer(string='الكمية القصوى')
    sc_heat        = fields.Boolean(string='حساس للحرارة')
    sc_light       = fields.Boolean(string='حساس للضوء')
    sc_dry         = fields.Boolean(string='يحتاج مكان جاف')
    sc_fragile     = fields.Boolean(string='قابل للكسر')
    sc_flammable   = fields.Boolean(string='قابل للاشتعال')
    sc_sterile     = fields.Boolean(string='يحتاج تعقيم')
    expiry_months  = fields.Integer(string='مدة الصلاحية (شهر)')

    # ── 14  الربط التشغيلي ─────────────────────────────────────────────────────
    op_purchase_req      = fields.Boolean(string='يظهر في طلبات الشراء (تشغيلي)')
    op_dispense_req       = fields.Boolean(string='يظهر في طلبات الصرف')
    op_internal_transfer  = fields.Boolean(string='يظهر في التحويل الداخلي')
    op_pharmacy           = fields.Boolean(string='يظهر في الصيدلية (تشغيلي)')
    op_clinics            = fields.Boolean(string='يظهر في العيادات')
    op_lab                = fields.Boolean(string='يظهر في المعمل')
    op_radiology          = fields.Boolean(string='يظهر في الأشعة')
    op_physiotherapy      = fields.Boolean(string='يظهر في العلاج الطبيعي')
    op_dashboard          = fields.Boolean(string='يظهر في Dashboard المخزون')
    op_dispense_approval  = fields.Boolean(string='يحتاج اعتماد عند الصرف')
    op_transfer_approval  = fields.Boolean(string='يحتاج اعتماد عند التحويل')
    op_dept_dispense      = fields.Boolean(string='يسمح بالصرف للأقسام')
    op_custody_dispense   = fields.Boolean(string='يسمح بالصرف للعهدة')
    op_consumed_on_use    = fields.Boolean(string='يستهلك عند الاستخدام')

    # ── 15  المحاسبة (معلوماتي فقط — لا يرتبط بمحرك المحاسبة الفعلي) ───────────
    cost_center      = fields.Char(string='Cost Center')
    analytic_account = fields.Char(string='Analytic Account')
    acc_inventory    = fields.Char(string='حساب المخزون')
    acc_expense      = fields.Char(string='حساب المصروف')
    acc_cogs         = fields.Char(string='حساب تكلفة البضاعة')
    acc_income       = fields.Char(string='حساب الإيراد')

    # ── 16  المرفقات والملاحظات ────────────────────────────────────────────────
    notes_internal  = fields.Text(string='ملاحظات داخلية')
    notes_warehouse = fields.Text(string='ملاحظات للمخزن')
    notes_user      = fields.Text(string='ملاحظات للمستخدم')
    pack_units_json  = fields.Text(string='وحدات التعبئة (JSON)')
    attachments_json = fields.Text(string='مرفقات الصنف (JSON)')
    suppliers_json   = fields.Text(string='الموردون (JSON)',
                                    help='قائمة موردين نصية بسيطة من شاشة الأصناف — لا ترتبط بسجلات res.partner فعلية')

    # ── 17  بيانات الخدمة ──────────────────────────────────────────────────────
    service_duration = fields.Char(string='مدة الخدمة')
    bookable         = fields.Boolean(string='إمكانية الحجز / الربط بمواعيد')


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
