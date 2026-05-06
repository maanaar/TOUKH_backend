# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareLabOrder(models.Model):
    _name = 'saycare.lab.order'
    _description = 'Laboratory Order'
    _order = 'requested_at desc, id desc'

    visit_id = fields.Many2one('saycare.visit', string='Visit', required=True, ondelete='cascade', index=True)
    patient_id = fields.Many2one('res.partner', string='Patient', related='visit_id.patient_id', store=True, index=True)
    
    test_name = fields.Char(string='Test Name', required=True)
    test_code = fields.Char(string='Test Code')
    
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ], string='Priority', default='normal', index=True)
    
    notes = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', index=True)
    
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, required=True)
    requested_at = fields.Datetime(string='Requested At', default=fields.Datetime.now, required=True)
