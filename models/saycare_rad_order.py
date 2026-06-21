# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareRadOrder(models.Model):
    _name        = 'saycare.rad.order'
    _description = 'Radiology Order'
    _order       = 'requested_at desc'

    visit_id            = fields.Many2one('saycare.visit',  ondelete='cascade',  index=True)
    patient_id          = fields.Many2one('res.partner',    ondelete='restrict', index=True,
                                          domain=[('is_patient', '=', True)])
    study_type          = fields.Char(string='Study Type', required=True)
    body_part           = fields.Char(string='Body Part')
    clinical_indication = fields.Text(string='Clinical Indication')
    notes               = fields.Text(string='Notes')
    state               = fields.Selection([
        ('requested',  'مطلوب'),
        ('scheduled',  'مجدول'),
        ('done',       'منجز'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='requested', index=True)
    result_notes        = fields.Text(string='Result Notes')
    result_at           = fields.Datetime(string='Result At')
    requested_by        = fields.Many2one('hr.employee', string='Requested By')
    requested_at        = fields.Datetime(string='Requested At', default=fields.Datetime.now)
