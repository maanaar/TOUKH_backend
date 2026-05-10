# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareLabOrder(models.Model):

    _name        = 'saycare.lab.order'
    _description = 'Laboratory Order'
    _order       = 'requested_at desc'

    visit_id     = fields.Many2one('saycare.visit',  ondelete='cascade',  index=True)
    patient_id   = fields.Many2one('res.partner',    ondelete='restrict', index=True,
                                   domain=[('is_patient', '=', True)])
    test_name    = fields.Char(string='Test Name', required=True)
    test_code    = fields.Char(string='Test Code')
    priority     = fields.Selection([
        ('routine', 'روتيني'),
        ('urgent',  'عاجل'),
        ('stat',    'فوري'),
    ], string='Priority', default='routine')
    notes        = fields.Text(string='Notes')
    state        = fields.Selection([
        ('requested',  'مطلوب'),
        ('collected',  'تم التحصيل'),
        ('resulted',   'النتائج جاهزة'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='requested', index=True)
    result_value  = fields.Text(string='Result')
    result_at     = fields.Datetime(string='Result At')
    requested_by  = fields.Many2one('hr.employee', string='Requested By')
    requested_at  = fields.Datetime(string='Requested At', default=fields.Datetime.now)
