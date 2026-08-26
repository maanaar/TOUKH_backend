# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareSpecialty(models.Model):
    _name        = 'saycare.specialty'
    _description = 'Medical Specialty / Clinic'
    _order       = 'name'

    name          = fields.Char(string='Specialty Name', required=True, translate=True)
    code          = fields.Char(string='Code')
    active        = fields.Boolean(default=True)
    description   = fields.Text(string='Description')
    room_number   = fields.Char(string='Room / Location')
    color         = fields.Integer(string='Color Index', default=0)

    categ_id      = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Product category that holds this clinic\'s consumables/supplies',
    )

    location_id   = fields.Many2one(
        'stock.location',
        string='الموقع',
        domain=[('usage', '=', 'internal')],
        help='موقع المخزون الذي تُصرف منه أصناف هذه العيادة — يُستخدم لتصفية قائمة المنتجات في شاشة الطبيب. '
             'يمكن اختيار موقع مخزن كامل أو موقع فرعي أدق منه.',
    )

    consultant_price           = fields.Float(string='سعر كشف الاستشاري', default=0.0)
    consultant_insurance_price = fields.Float(string='حصة تأمين الاستشاري', default=0.0)
    specialist_price           = fields.Float(string='سعر كشف الأخصائي', default=0.0)
    specialist_insurance_price = fields.Float(string='حصة تأمين الأخصائي', default=0.0)

    doctor_ids    = fields.One2many(
        'hr.employee', 'specialty_id',
        string='Doctors',
        domain=[('medical_role', '=', 'doctor')],
    )

    service_ids   = fields.One2many(
        'saycare.service', 'specialty_id',
        string='Services',
    )

    product_count = fields.Integer(
        string='عدد الخدمات',
        compute='_compute_product_count',
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Specialty name must be unique.'),
    ]

    @api.depends('categ_id')
    def _compute_product_count(self):
        Product = self.env['product.template'].sudo()
        for rec in self:
            if rec.categ_id:
                rec.product_count = Product.search_count([
                    ('categ_id', 'child_of', rec.categ_id.id),
                    ('active', '=', True),
                ])
            else:
                rec.product_count = 0

    def action_view_products(self):
        self.ensure_one()
        return {
            'name': f'خدمات {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('categ_id', 'child_of', self.categ_id.id)],
            'context': {
                'default_categ_id': self.categ_id.id,
                'default_type': 'service',
                'default_sale_ok': True,
            },
        }

    def _sync_services_from_categ(self):
        """Create saycare.service rows for every product in categ_id that
        does not already have one under this specialty."""
        Service = self.env['saycare.service'].sudo()
        Categ   = self.env['product.category'].sudo()
        Product = self.env['product.template'].sudo()
        for specialty in self:
            if not specialty.categ_id:
                continue
            categ_ids = Categ.search([('id', 'child_of', specialty.categ_id.id)]).ids
            products  = Product.search([
                ('categ_id', 'in', categ_ids),
                ('active',   '=', True),
            ])
            existing_product_ids = specialty.service_ids.mapped('product_id').ids
            for product in products:
                if product.id not in existing_product_ids:
                    Service.create({
                        'name':         product.name,
                        'price':        product.list_price,
                        'code':         product.default_code or '',
                        'specialty_id': specialty.id,
                        'product_id':   product.id,
                    })

    def action_sync_services(self):
        self._sync_services_from_categ()
        return True

    def write(self, vals):
        res = super().write(vals)
        if 'categ_id' in vals:
            self._sync_services_from_categ()
        return res


class HrEmployeeMedical(models.Model):
    _inherit = 'hr.employee'

    medical_role = fields.Selection([
        ('doctor',        'طبيب'),
        ('nurse',         'ممرض/ة'),
        ('receptionist',  'موظف استقبال'),
        ('pharmacist',    'صيدلاني'),
        ('lab_tech',      'تحاليل'),
        ('rad_tech',      'أشعة'),
    ], string='Medical Role')

    doctor_grade = fields.Selection([
        ('consultant', 'استشاري'),
        ('specialist', 'أخصائي'),
    ], string='درجة الطبيب')

    # ── Warehouse access (نقل للمخازن الفرعية / طلبات صرف واستلام الأقسام) ──
    # An employee can be assigned more than one warehouse (e.g. covers both
    # مخازن مستلزمات and مخزن الصيدلية) - scopes which sub-warehouse locations
    # they're allowed to receive transfers into.
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='المخازن المخصصة',
    )

    specialty_id    = fields.Many2one('saycare.specialty', string='Specialty')
    license_number  = fields.Char(string='Medical License No.')

    # Which clinics a nurse is assigned to cover — separate from specialty_id
    # (that field is doctor-only: saycare.specialty.doctor_ids is a One2many
    # inverse of it, so repurposing it for nurses would break every doctor
    # picker in the app). A nurse can cover more than one clinic; the نظام
    # التمريض queue (NursingPage.jsx) only shows visits for clinics listed here.
    nurse_specialty_ids = fields.Many2many(
        'saycare.specialty', string='العيادات المسؤول عنها (تمريض)',
    )
