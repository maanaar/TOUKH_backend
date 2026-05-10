# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareAppointment(models.Model):
    _name        = 'saycare.appointment'
    _description = 'Appointment'
    _order       = 'date desc, start_time desc'
    _rec_name    = 'name'

    name         = fields.Char(string='Appointment Ref', readonly=True, default='New', copy=False)
    patient_id   = fields.Many2one('res.partner', string='Patient', required=True,
                                   domain=[('is_patient', '=', True)],
                                   ondelete='restrict', index=True)
    doctor_id    = fields.Many2one('hr.employee', string='Doctor',
                                   domain=[('medical_role', '=', 'doctor')])
    specialty_id = fields.Many2one('saycare.specialty', string='Specialty')
    date         = fields.Date(string='Date', required=True, index=True)
    start_time   = fields.Float(string='Start Time')
    end_time     = fields.Float(string='End Time')
    visit_type   = fields.Selection([
        ('outpatient', 'عيادات خارجية'),
        ('inpatient',  'داخلي'),
        ('emergency',  'طوارئ'),
    ], string='Visit Type', default='outpatient')
    state        = fields.Selection([
        ('scheduled',  'مجدول'),
        ('confirmed',  'مؤكد'),
        ('arrived',    'حضر'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='scheduled', index=True)
    visit_id     = fields.Many2one('saycare.visit', string='Visit', ondelete='set null')
    notes        = fields.Text(string='Notes')

    def create(self, vals_list):
        for vals in (vals_list if isinstance(vals_list, list) else [vals_list]):
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saycare.appointment') or 'New'
        return super().create(vals_list)
