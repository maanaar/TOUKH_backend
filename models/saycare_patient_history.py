# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycarePatientAllergy(models.Model):
    _name        = 'saycare.patient.allergy'
    _description = 'Patient Allergy'
    _order       = 'id desc'

    patient_id = fields.Many2one('res.partner', required=True, ondelete='cascade',
                                 index=True, domain=[('is_patient', '=', True)])
    allergen   = fields.Char(string='Allergen', required=True)
    reaction   = fields.Char(string='Reaction')
    severity   = fields.Selection([
        ('mild',     'خفيف'),
        ('moderate', 'متوسط'),
        ('severe',   'شديد'),
    ], string='Severity', default='mild')
    active     = fields.Boolean(default=True)


class SaycarePatientCondition(models.Model):
    _name        = 'saycare.patient.condition'
    _description = 'Patient Chronic Condition'
    _order       = 'id desc'

    patient_id = fields.Many2one('res.partner', required=True, ondelete='cascade',
                                 index=True, domain=[('is_patient', '=', True)])
    name       = fields.Char(string='Condition', required=True)
    icd_code   = fields.Char(string='ICD Code')
    since_date = fields.Date(string='Since')
    active     = fields.Boolean(default=True)
    notes      = fields.Text(string='Notes')


class SaycarePatientSurgery(models.Model):
    _name        = 'saycare.patient.surgery'
    _description = 'Patient Surgical History'
    _order       = 'procedure_date desc'

    patient_id     = fields.Many2one('res.partner', required=True, ondelete='cascade',
                                     index=True, domain=[('is_patient', '=', True)])
    procedure_name = fields.Char(string='Procedure', required=True)
    procedure_date = fields.Date(string='Date')
    hospital       = fields.Char(string='Hospital')
    notes          = fields.Text(string='Notes')


class SaycarePatientMedication(models.Model):
    _name        = 'saycare.patient.medication'
    _description = 'Patient Current Medication'
    _order       = 'id desc'

    patient_id = fields.Many2one('res.partner', required=True, ondelete='cascade',
                                 index=True, domain=[('is_patient', '=', True)])
    drug_name  = fields.Char(string='Drug', required=True)
    dose       = fields.Char(string='Dose')
    frequency  = fields.Char(string='Frequency')
    start_date = fields.Date(string='Since')
    active     = fields.Boolean(default=True)
