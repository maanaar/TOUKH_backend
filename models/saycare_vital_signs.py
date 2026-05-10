# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareVitalSigns(models.Model):
    _name        = 'saycare.vital.signs'
    _description = 'Vital Signs'
    _order       = 'recorded_at desc'

    visit_id         = fields.Many2one('saycare.visit', ondelete='cascade', index=True)
    blood_pressure   = fields.Char(string='Blood Pressure')
    temperature      = fields.Float(string='Temperature (°C)')
    pulse            = fields.Integer(string='Pulse (bpm)')
    respiratory_rate = fields.Integer(string='Respiratory Rate')
    respiratory_type = fields.Selection([
        ('normal', 'طبيعي'),
        ('fast',   'سريع'),
        ('slow',   'بطيء'),
    ], string='Respiratory Type', default='normal')
    o2_saturation    = fields.Float(string='O2 Saturation (%)')
    weight           = fields.Float(string='Weight (kg)')
    height           = fields.Float(string='Height (cm)')
    bmi              = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    recorded_by      = fields.Many2one('hr.employee', string='Recorded By')
    recorded_at      = fields.Datetime(string='Recorded At', default=fields.Datetime.now)

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.height and rec.weight:
                h_m = rec.height / 100.0
                rec.bmi = round(rec.weight / (h_m * h_m), 2)
            else:
                rec.bmi = 0.0
