# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerPatient(models.Model):
    _inherit = 'res.partner'

    # ── Patient flag ──────────────────────────────────────────────────────────
    is_patient = fields.Boolean(string='Patient', default=False, index=True)

    # ── Patient type (mutually exclusive) ─────────────────────────────────────
    patient_type = fields.Selection([
        ('normal',    'مريض عادي'),
        ('foreigner', 'أجنبي'),
        ('unknown',   'مجهول الهوية'),
        ('baby',      'طفل'),
    ], string='Patient Type', default='normal')

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

    # ── Financial class ───────────────────────────────────────────────────────
    financial_class = fields.Selection([
        ('cash',          'نقدي'),
        ('state_expense', 'نفقة الدولة'),
        ('consultation',  'مشورة'),
        ('takaful',       'تكافل وكرامة'),
        ('insurance',     'تأمين صحي'),
        ('contract',      'تعاقدات'),
    ], string='Financial Class', default='cash')

    insurance_company = fields.Char(string='Insurance Company')
    contract_entity   = fields.Char(string='Contract Entity')
