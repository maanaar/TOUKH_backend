# -*- coding: utf-8 -*-
from odoo import models, fields, api


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
        ('outpatient',   'كشف'),
        ('inpatient',    'داخلي'),
        ('emergency',    'طوارئ'),
        ('consultation', 'استشارة'),
    ], string='نوع الزيارة', default='outpatient')

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
        ('insurance',    'تأمين صحى'),
        ('contract',     'تعاقدات'),
        ('moh',          'وزارة الصحة'),
        ('staff',        'عاملين'),
    ], string='الوجهة المالية')

    payment_method = fields.Selection([
        ('cash',     'نقدي'),
        ('deferred', 'مميكن'),
    ], string='طريقة الدفع', default='cash')

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

    # ── Financial detail fields ────────────────────────────────────────────────
    decision_no        = fields.Char(string='رقم القرار')
    expiry_date        = fields.Date(string='تاريخ الانتهاء')
    available_balance  = fields.Float(string='الرصيد المتاح')
    covered_services   = fields.Char(string='الخدمات المغطاة')
    contract_entity    = fields.Char(string='جهة التعاقد')
    co_pay_percent     = fields.Char(string='نسبة التحمل')
    approval_required  = fields.Boolean(string='يتطلب موافقة', default=False)
    admin_letter_no    = fields.Char(string='رقم الخطاب الإداري')
    issuing_authority  = fields.Char(string='جهة الإصدار')
    card_number        = fields.Char(string='رقم الكارت')
    financial_notes    = fields.Text(string='ملاحظات مالية')
    employee_id_no     = fields.Char(string='الرقم الوظيفي')
    department         = fields.Char(string='الإدارة / القسم')

    invoice_id  = fields.Many2one('account.move', string='Invoice', ondelete='set null')

    service_ids = fields.Many2many(
        'saycare.service', 'saycare_visit_service_rel',
        'visit_id', 'service_id',
        string='Services',
    )

    total_price     = fields.Float(string='Total Price',     compute='_compute_totals', store=True)
    insurance_share = fields.Float(string='Insurance Share', compute='_compute_totals', store=True)
    patient_share   = fields.Float(string='Patient Share',   compute='_compute_totals', store=True)

    @api.depends('service_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_price     = sum(rec.service_ids.mapped('price'))
            rec.insurance_share = sum(rec.service_ids.mapped('insurance_price'))
            rec.patient_share   = max(0.0, rec.total_price - rec.insurance_share)

    def create(self, vals_list):
        for vals in (vals_list if isinstance(vals_list, list) else [vals_list]):
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saycare.visit') or 'New'
        return super().create(vals_list)
