# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareClinicalNote(models.Model):
    _name = 'saycare.clinical.note'
    _description = 'Clinical Note'
    _order = 'create_date desc, id desc'

    visit_id = fields.Many2one('saycare.visit', string='Visit', required=True, ondelete='cascade', index=True)
    
    chief_complaint = fields.Text(string='Chief Complaint')
    complaint_duration = fields.Char(string='Complaint Duration')
    complaint_severity = fields.Selection([
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Complaint Severity', default='moderate')
    
    associated_symptoms = fields.Text(string='Associated Symptoms')
    
    primary_diagnosis = fields.Text(string='Primary Diagnosis')
    secondary_diagnosis = fields.Text(string='Secondary Diagnosis')
    differential_diagnosis = fields.Text(string='Differential Diagnosis')
    
    clinical_impression = fields.Text(string='Clinical Impression')
    management_plan = fields.Text(string='Management Plan')
    followup_instructions = fields.Text(string='Follow-up Instructions')
