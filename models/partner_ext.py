# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api


class ResPartnerPatient(models.Model):
    _inherit = 'res.partner'

    # ── Patient flag ──────────────────────────────────────────────────────────
    is_patient = fields.Boolean(string='Patient', default=False, index=True)

    # ── Patient type (mutually exclusive) ─────────────────────────────────────
    patient_type = fields.Selection([
        ('normal',    'مصري'),
        ('foreigner', 'أجنبي'),
        ('unknown',   'مجهول الهوية'),
        ('baby',      'طفل'),
    ], string='Nationality', default='normal')

    age_group = fields.Selection([
        ('adult', 'بالغ'),
        ('child', 'طفل'),
    ], string='Age Group', compute='_compute_age_group', store=True)

    @api.depends('patient_type')
    def _compute_age_group(self):
        for rec in self:
            rec.age_group = 'child' if rec.patient_type == 'baby' else 'adult'

    # ── Medical Record Number ─────────────────────────────────────────────────
    mrn = fields.Char(string='MRN', copy=False, index=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    id_type = fields.Selection([
        ('national_id', 'رقم قومي'),
        ('passport',    'جواز سفر'),
    ], string='ID Type', default='national_id')

    id_number = fields.Char(string='ID Number')

    # ── Name parts ────────────────────────────────────────────────────────────
    first_name  = fields.Char(string='First Name')
    second_name = fields.Char(string='Second Name')
    third_name  = fields.Char(string='Third Name')
    last_name   = fields.Char(string='Last Name')

    # ── Demographics ──────────────────────────────────────────────────────────
    dob = fields.Date(string='Date of Birth')

    gender = fields.Selection([
        ('male',   'ذكر'),
        ('female', 'أنثى'),
    ], string='Gender')

    home_phone  = fields.Char(string='Home Phone')
    occupation  = fields.Char(string='Occupation')

    # ── Address ───────────────────────────────────────────────────────────────
    governorate = fields.Char(string='Governorate')
    # ── Medical ───────────────────────────────────────────────────────────────
    x_blood_type = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ], string='Blood Type')
    # blood_type = fields.Selection([
    #         ('A+', 'A+'), ('A-', 'A-'),
    #         ('B+', 'B+'), ('B-', 'B-'),
    #         ('AB+', 'AB+'), ('AB-', 'AB-'),
    #         ('O+', 'O+'), ('O-', 'O-'),
    #     ], string='Blood Type')
    # ── Financial class ───────────────────────────────────────────────────────
    financial_class = fields.Selection([
        ('cash',         'نقدي'),
        ('state',        'نفقة الدولة'),
        ('consultation', 'مشورة'),
        ('takaful',      'تكافل وكرامة'),
        ('insurance',    'تأمين صحى'),
        ('contract',     'تعاقدات'),
        ('moh',          'وزارة الصحة'),
        ('staff',        'عاملين'),
    ], string='الوجهة المالية', default='cash')

    insurance_company = fields.Char(string='Insurance Company')
    contract_entity   = fields.Char(string='Contract Entity')
    is_vendor = fields.Boolean(
        string='مصنّع / مورد رئيسي',
        default=False,
        help='تحديد هذا الحقل يجعل الشريك يظهر في قائمة الشركة المصنّعة',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_patient') and not vals.get('mrn'):
                vals['mrn'] = self._next_mrn()
        return super().create(vals_list)

    def _next_mrn(self):
        last = self.search(
            [('is_patient', '=', True), ('mrn', '!=', False)],
            order='id desc', limit=1,
        )
        if last and last.mrn:
            m = re.search(r'(\d+)$', last.mrn)
            if m:
                return f'MRN{int(m.group(1)) + 1:06d}'
        return self.env['ir.sequence'].next_by_code('saycare.patient.mrn') or 'MRN000001'
