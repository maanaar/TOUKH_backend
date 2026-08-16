# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareClinicalNote(models.Model):
    _name        = 'saycare.clinical.note'
    _description = 'Clinical Note'
    _order       = 'written_at desc'

    visit_id               = fields.Many2one('saycare.visit', ondelete='cascade', index=True)
    chief_complaint        = fields.Text(string='Chief Complaint')
    complaint_duration     = fields.Char(string='Duration')
    complaint_severity     = fields.Selection([
        ('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),
        ('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),
    ], string='Severity (1-10)')
    associated_symptoms    = fields.Text(string='Associated Symptoms')
    nursing_notes          = fields.Text(string='Nursing Notes')

    primary_diagnosis_code = fields.Char(string='Primary Diagnosis Code')
    primary_diagnosis_desc = fields.Char(string='Primary Diagnosis')
    secondary_diagnoses    = fields.Text(string='Secondary Diagnoses (JSON)')
    differential_diagnoses = fields.Text(string='Differential Diagnoses (JSON)')

    clinical_impression    = fields.Text(string='Clinical Impression')
    management_plan        = fields.Text(string='Management Plan')
    followup_instructions  = fields.Text(string='Follow-up Instructions')

    med_conditions         = fields.Text(string='Medical Conditions (JSON)')
    surgical_history       = fields.Text(string='Surgical History (JSON)')
    current_medications    = fields.Text(string='Current Medications (JSON)')
    allergies              = fields.Text(string='Allergies (JSON)')

    written_by             = fields.Many2one('hr.employee', string='Written By')
    written_at             = fields.Datetime(string='Written At', default=fields.Datetime.now)
