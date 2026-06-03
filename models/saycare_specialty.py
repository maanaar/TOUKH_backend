# -*- coding: utf-8 -*-
from odoo import models, fields


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

    # Link to product.category so inventory products for this clinic can be filtered
    categ_id      = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Product category that holds this clinic\'s consumables/supplies',
    )

    # Doctors assigned to this clinic
    doctor_ids    = fields.One2many(
        'hr.employee', 'specialty_id',
        string='Doctors',
        domain=[('medical_role', '=', 'doctor')],
    )

    # Services offered by this clinic (reverse of saycare.service.specialty_id)
    service_ids   = fields.One2many(
        'saycare.service', 'specialty_id',
        string='Services',
    )

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
