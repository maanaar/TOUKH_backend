# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareVisit(models.Model):
    _name        = 'saycare.visit'
    _description = 'Patient Visit'
    _order       = 'admission_date desc, id desc'
    _rec_name    = 'name'

    name           = fields.Char(string='Visit Reference', required=True, copy=False,
                                 readonly=True, default='New')
    patient_id     = fields.Many2one('res.partner', string='Patient',
                                     domain=[('is_patient', '=', True)],
                                     ondelete='restrict', index=True, required=True)
    admission_date = fields.Datetime(string='Admission Date', default=fields.Datetime.now, index=True)
    discharge_date = fields.Datetime(string='Discharge Date')

    state = fields.Selection([
        ('draft',      'مسودة'),
        ('admitted',   'مقيم'),
        ('discharged', 'خروج'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='draft', index=True)

    visit_type = fields.Selection([
        ('outpatient', 'عيادات خارجية'),
        ('inpatient',  'داخلي'),
        ('emergency',  'طوارئ'),
    ], string='Visit Type', default='outpatient')

    specialty_id = fields.Many2one('saycare.specialty', string='Specialty')
    doctor_id    = fields.Many2one('hr.employee', string='Doctor',
                                   domain=[('medical_role', '=', 'doctor')])

    medication_order_ids = fields.One2many('saycare.medication.order', 'visit_id',
                                           string='Medication Orders')

    notes = fields.Text(string='Notes')

    def create(self, vals_list):
        for vals in (vals_list if isinstance(vals_list, list) else [vals_list]):
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saycare.visit') or 'New'
        return super().create(vals_list)
