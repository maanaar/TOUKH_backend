# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareAdmissionRequest(models.Model):
    _name        = 'saycare.admission.request'
    _description = 'Admission / Internal Transfer Request'
    _order       = 'create_date desc'
    _rec_name    = 'patient_name'

    # ── Identity / link ──────────────────────────────────────────────────────
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 domain=[('is_patient', '=', True)], index=True)

    source = fields.Selection([
        ('opd',               'محولة من OPD'),
        ('operation_booking', 'حجز عملية مباشر'),
    ], string='Source', default='opd', index=True)

    status = fields.Selection([
        ('pending_admission', 'في انتظار القبول'),
        ('admitted',          'تم القبول'),
        ('cancelled',         'ملغي'),
    ], string='Status', default='pending_admission', index=True)

    # ── Patient snapshot ──────────────────────────────────────────────────────
    patient_name    = fields.Char(string='اسم المريض')
    file_number     = fields.Char(string='رقم الملف')
    entry_permit_no = fields.Char(string='إذن الدخول')
    national_id     = fields.Char(string='الرقم القومي')
    opd_visit_number = fields.Char(string='رقم زيارة الخارجي')
    patient_mrn     = fields.Char(string='Patient MRN')
    patient_mobile  = fields.Char(string='الهاتف')
    age             = fields.Char(string='العمر')
    gender          = fields.Char(string='النوع')
    address         = fields.Char(string='العنوان')

    # ── Payment ───────────────────────────────────────────────────────────────
    payment_type      = fields.Char(string='طريقة الدفع')
    contract_entity    = fields.Char(string='جهة التعاقد')
    co_pay_percent     = fields.Char(string='نسبة التحمل')
    approval_required  = fields.Boolean(string='يتطلب موافقة', default=False)

    # ── Booking classification ──────────────────────────────────────────────
    is_inpatient = fields.Boolean(string='دخول', default=False)
    is_operation = fields.Boolean(string='عملية', default=False)

    transfer_type    = fields.Char(string='تصنيف العملية')
    operation_name   = fields.Char(string='اسم العملية')
    operation_reason  = fields.Char(string='سبب العملية')

    # ── Inpatient booking targets (set by OperationBookingPage only) ────────
    department_id = fields.Many2one('hospital.inpatient.department', string='القسم')
    floor_id      = fields.Many2one('hospital.floor', string='الدور')
    stay_grade_id = fields.Many2one('hospital.accommodation.grade', string='درجة الإقامة')
    room_id       = fields.Many2one('hospital.room', string='الغرفة')
    bed_id        = fields.Many2one('hospital.bed', string='السرير')

    # ── Clinical ─────────────────────────────────────────────────────────────
    diagnosis                = fields.Text(string='التشخيص')
    reason                   = fields.Text(string='سبب الدخول / العملية')
    doctor_decision_notes    = fields.Text(string='ملاحظات الطبيب')
    transfer_decision_reason = fields.Text(string='سبب قرار التحويل')

    booking_datetime = fields.Datetime(string='ميعاد الحجز')

    surgeon_id     = fields.Many2one('hr.employee', string='الجراح',
                                     domain=[('medical_role', '=', 'doctor')])
    surgeon_name   = fields.Char(string='اسم الجراح')
    doctor_name    = fields.Char(string='اسم الطبيب')
    priority       = fields.Char(string='الأولوية')
    anesthesia_type = fields.Char(string='نوع التخدير')

    # ── Pre-admission planning ──────────────────────────────────────────────
    expected_admission_date = fields.Date(string='تاريخ الدخول المتوقع')
    expected_discharge_date = fields.Date(string='تاريخ الخروج المتوقع')
    max_stay_days           = fields.Integer(string='مدة الإقامة القصوى')

    # ── References ───────────────────────────────────────────────────────────
    inpatient_booking_number = fields.Char(string='رقم حجز الداخلي', copy=False, readonly=True)
    operation_booking_number = fields.Char(string='رقم حجز العملية', copy=False, readonly=True)

    # ── Admission-time fields (set only via the admit action) ──────────────
    ward             = fields.Char(string='القسم (تسكين)')
    bed              = fields.Char(string='السرير (تسكين)')
    attending_doctor = fields.Char(string='طبيب الدخول')
    admission_date   = fields.Date(string='تاريخ الدخول')
    admission_notes  = fields.Text(string='ملاحظات القبول')
    admitted_at      = fields.Datetime(string='وقت القبول', copy=False, readonly=True)

    # ── Rejection (set only via the reject action) ─────────────────────────
    rejection_reason = fields.Text(string='سبب الرفض')
    rejected_at      = fields.Datetime(string='وقت الرفض', copy=False, readonly=True)

    # ── Critical care ────────────────────────────────────────────────────────
    is_transfer = fields.Boolean(string='دخول عن طريق تحويل', default=False)

    # ── Nursing worklist ─────────────────────────────────────────────────────
    visit_id = fields.Many2one('saycare.visit', string='الزيارة', copy=False)
    worklist_stage = fields.Selection([
        ('booked', 'محجوز'),
        ('admission_done', 'تم القبول'),
        ('awaiting_nursing', 'بانتظار التمريض'),
        ('received_by_ward', 'تم الاستلام بالقسم'),
        ('under_assessment', 'تحت التقييم'),
        ('ready_for_operation', 'جاهز للعملية'),
        ('discharge_planning', 'تخطيط الخروج'),
    ], string='مرحلة قائمة التمريض', default='booked', index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_inpatient') and not vals.get('inpatient_booking_number'):
                vals['inpatient_booking_number'] = \
                    self.env['ir.sequence'].next_by_code('saycare.admission.request.inpatient') or False
            if vals.get('is_operation') and not vals.get('operation_booking_number'):
                vals['operation_booking_number'] = \
                    self.env['ir.sequence'].next_by_code('saycare.admission.request.operation') or False
        return super().create(vals_list)
