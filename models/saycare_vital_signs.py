# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareVitalSigns(models.Model):
    _name = 'saycare.vital.signs'
    _description = 'Vital Signs'
    _order = 'recorded_at desc, id desc'

    visit_id = fields.Many2one('saycare.visit', string='Visit', required=True, ondelete='cascade', index=True)
    
    blood_pressure = fields.Char(string='Blood Pressure')
    temperature = fields.Float(string='Temperature (°C)')
    pulse = fields.Integer(string='Pulse (bpm)')
    respiratory_rate = fields.Integer(string='Respiratory Rate (bpm)')
    respiratory_type = fields.Selection([
        ('normal', 'Normal'),
        ('labored', 'Labored'),
        ('shallow', 'Shallow'),
        ('deep', 'Deep'),
        ('other', 'Other'),
    ], string='Respiratory Type', default='normal')
    o2_saturation = fields.Float(string='O2 Saturation (%)')
    
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    
    recorded_by = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user, required=True)
    recorded_at = fields.Datetime(string='Recorded At', default=fields.Datetime.now, required=True)

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for record in self:
            if record.height > 0:
                # BMI = weight (kg) / [height (m)]^2
                record.bmi = record.weight / ((record.height / 100) ** 2)
            else:
                record.bmi = 0.0
