# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareSpecialty(models.Model):
    _name        = 'saycare.specialty'
    _description = 'Medical Specialty'
    _order       = 'name'

    name   = fields.Char(string='Specialty Name', required=True, translate=True)
    code   = fields.Char(string='Code')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Specialty name must be unique.'),
    ]


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

    specialty_id    = fields.Many2one('saycare.specialty', string='Specialty')
    license_number  = fields.Char(string='Medical License No.')
