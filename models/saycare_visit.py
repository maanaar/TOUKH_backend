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
        ('waiting',      'في الانتظار'),
        ('triage',       'قيد التقييم'),
        ('doctor_queue', 'انتظار الطبيب'),
        ('in_progress',  'قيد الفحص'),
        ('done',         'مكتمل'),
        ('cancelled',    'ملغي'),
    ], string='Status', default='waiting', index=True)

    visit_type = fields.Selection([
        ('outpatient',   'عيادات خارجية'),
        ('inpatient',    'داخلي'),
        ('emergency',    'طوارئ'),
        ('consultation', 'مشورة'),
    ], string='Visit Type', default='outpatient')

    specialty_id = fields.Many2one('saycare.specialty', string='Specialty')
    doctor_id    = fields.Many2one('hr.employee', string='Doctor',
                                   domain=[('medical_role', '=', 'doctor')])
    nurse_id     = fields.Many2one('hr.employee', string='Nurse',
                                   domain=[('medical_role', '=', 'nurse')])

    financial_class = fields.Selection([
        ('cash',         'نقدي'),
        ('state',        'نفقة الدولة'),
        ('consultation', 'مشورة'),
        ('takaful',      'تكافل وكرامة'),
        ('insurance',    'تأمين صحي'),
        ('contract',     'تعاقدات'),
    ], string='Financial Class')

    chief_complaint = fields.Char(string='Chief Complaint')
    triage_notes    = fields.Text(string='Triage Notes')

    medication_order_ids = fields.One2many('saycare.medication.order', 'visit_id',
                                           string='Medication Orders')
    vital_sign_ids       = fields.One2many('saycare.vital.signs',    'visit_id',
                                           string='Vital Signs')
    clinical_note_ids    = fields.One2many('saycare.clinical.note',  'visit_id',
                                           string='Clinical Notes')
    lab_order_ids        = fields.One2many('saycare.lab.order',      'visit_id',
                                           string='Lab Orders')
    rad_order_ids        = fields.One2many('saycare.rad.order',      'visit_id',
                                           string='Rad Orders')

    notes = fields.Text(string='Notes')

    def create(self, vals_list):
        for vals in (vals_list if isinstance(vals_list, list) else [vals_list]):
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saycare.visit') or 'New'
        return super().create(vals_list)
