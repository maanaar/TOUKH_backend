# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareRadOrder(models.Model):
    _name = 'saycare.rad.order'
    _description = 'Radiology Order'
    _order = 'requested_at desc, id desc'

    visit_id = fields.Many2one('saycare.visit', string='Visit', required=True, ondelete='cascade', index=True)
    patient_id = fields.Many2one('res.partner', string='Patient', related='visit_id.patient_id', store=True, index=True)
    
    study_type = fields.Char(string='Study Type', required=True)
    body_part = fields.Char(string='Body Part')
    clinical_indication = fields.Text(string='Clinical Indication')
    
    notes = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', index=True)
    
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, required=True)
    requested_at = fields.Datetime(string='Requested At', default=fields.Datetime.now, required=True)
