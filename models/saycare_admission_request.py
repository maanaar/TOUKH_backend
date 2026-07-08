# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareAdmissionRequest(models.Model):
    _name = 'saycare.admission.request'
    _description = 'Internal Booking / Admission Request (حجز الداخلي - قبول المريض)'
    _order = 'create_date desc'

    source = fields.Selection([
        ('operation_booking', 'حجز عملية مباشر'),
        ('opd',                'محول من OPD'),
    ], string='المصدر', default='operation_booking', required=True)

    status = fields.Selection([
        ('pending_admission', 'في انتظار القبول'),
        ('admitted',          'تم القبول'),
        ('cancelled',         'ملغي'),
    ], string='الحالة', default='pending_admission', required=True)

    inpatient_booking_number = fields.Char(string='رقم حجز الداخلي', readonly=True, copy=False)
    operation_booking_number = fields.Char(string='رقم حجز العملية', readonly=True, copy=False)

    patient_id     = fields.Many2one('res.partner', string='المريض', ondelete='restrict')
    patient_name   = fields.Char(string='اسم المريض')
    national_id    = fields.Char(string='الرقم القومي')
    file_number    = fields.Char(string='رقم الملف')
    entry_permit_no = fields.Char(string='إذن الدخول')
    patient_mobile = fields.Char(string='الهاتف')
    age            = fields.Char(string='العمر')
    gender         = fields.Char(string='النوع')
    address        = fields.Char(string='العنوان')
    opd_visit_number = fields.Char(string='رقم زيارة الخارجي')

    payment_type      = fields.Char(string='المعاملة المالية')
    contract_entity    = fields.Char(string='جهة التعاقد')
    co_pay_percent     = fields.Char(string='نسبة التحمل')
    approval_required  = fields.Boolean(string='يتطلب موافقة؟')

    is_inpatient = fields.Boolean(string='حجز الداخلي')
    is_operation = fields.Boolean(string='حجز العمليات')
    transfer_type = fields.Char(string='تصنيف العملية')
    operation_name   = fields.Char(string='مسمى العملية')
    operation_reason = fields.Text(string='سبب دخول العملية')
    anesthesia_type  = fields.Char(string='نوع التخدير')

    department_id  = fields.Many2one('hospital.inpatient.department', string='القسم')
    floor_id       = fields.Many2one('hospital.floor', string='الدور')
    stay_grade_id  = fields.Many2one('hospital.accommodation.grade', string='درجة الإقامة')
    room_id        = fields.Many2one('hospital.room', string='الغرفة')
    bed_id         = fields.Many2one('hospital.bed', string='السرير')

    diagnosis = fields.Text(string='التشخيص')
    reason    = fields.Text(string='سبب الدخول')
    transfer_decision_reason = fields.Text(string='سبب قرار التحويل')

    booking_datetime        = fields.Datetime(string='ميعاد الحجز')
    expected_admission_date  = fields.Date(string='تاريخ الدخول المتوقع')
    expected_discharge_date  = fields.Date(string='تاريخ الخروج المتوقع')
    max_stay_days            = fields.Integer(string='مدة الإقامة القصوى')

    surgeon_id = fields.Many2one('hr.employee', string='الطبيب / الجراح')
    surgeon_name = fields.Char(string='اسم الجراح')
    doctor_name  = fields.Char(string='اسم الطبيب')
    doctor_decision_notes = fields.Text(string='ملاحظات الطبيب')
    priority = fields.Char(string='الأولوية', default='عادي')

    # ── Admission-time assignment (filled in "قبول المريض") ──────────────────
    admission_ward             = fields.Char(string='قسم الدخول')
    admission_bed              = fields.Char(string='سرير الدخول')
    admission_payment_type     = fields.Char(string='طريقة دفع الدخول')
    admission_attending_doctor = fields.Char(string='طبيب الدخول')
    admission_date             = fields.Date(string='تاريخ الدخول')
    admission_expected_discharge_date = fields.Date(string='تاريخ الخروج المتوقع (دخول)')
    admission_max_stay_days    = fields.Integer(string='مدة الإقامة القصوى (دخول)')
    admission_notes            = fields.Text(string='ملاحظات الدخول')

    admitted_at = fields.Datetime(string='وقت القبول')

    def create(self, vals_list):
        single = not isinstance(vals_list, list)
        vals_list_ = [vals_list] if single else vals_list
        for vals in vals_list_:
            ts = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
            if not vals.get('inpatient_booking_number'):
                vals['inpatient_booking_number'] = f'INP-{ts}'
            if not vals.get('operation_booking_number'):
                vals['operation_booking_number'] = f'OPR-{ts}'
        return super().create(vals_list_[0] if single else vals_list_)

    def _to_dict(self):
        self.ensure_one()
        return {
            'id':          self.id,
            'source':      self.source,
            'status':      self.status,
            'inpatientBookingNumber': self.inpatient_booking_number or '',
            'operationBookingNumber': self.operation_booking_number or '',
            'patientName':   self.patient_name or (self.patient_id.name if self.patient_id else ''),
            'nationalId':    self.national_id or '',
            'fileNumber':    self.file_number or '',
            'patientMrn':    self.file_number or '',
            'entryPermitNo': self.entry_permit_no or '',
            'patientMobile': self.patient_mobile or '',
            'age':           self.age or '',
            'gender':        self.gender or '',
            'address':       self.address or '',
            'opdVisitNumber': self.opd_visit_number or '',
            'paymentType':      self.payment_type or '',
            'contractEntity':   self.contract_entity or '',
            'coPayPercent':     self.co_pay_percent or '',
            'approvalRequired': self.approval_required,
            'isInpatient': self.is_inpatient,
            'isOperation': self.is_operation,
            'transferType':   self.transfer_type or '',
            'operationName':  self.operation_name or '',
            'operationReason': self.operation_reason or '',
            'anesthesiaType': self.anesthesia_type or '',
            'departmentId':   self.department_id.id if self.department_id else None,
            'departmentName': self.department_id.name_ar if self.department_id else '',
            'floorId':   self.floor_id.id if self.floor_id else None,
            'floorName': self.floor_id.name if self.floor_id else '',
            'stayGradeId':   self.stay_grade_id.id if self.stay_grade_id else None,
            'stayGradeName': self.stay_grade_id.name if self.stay_grade_id else '',
            'roomId':   self.room_id.id if self.room_id else None,
            'roomName': self.room_id.room_no if self.room_id else '',
            'bedId':   self.bed_id.id if self.bed_id else None,
            'bedName': self.bed_id.bed_no if self.bed_id else '',
            'diagnosis': self.diagnosis or '',
            'reason':    self.reason or '',
            'transferDecisionReason': self.transfer_decision_reason or self.reason or '',
            'bookingDateTime':       str(self.booking_datetime) if self.booking_datetime else '',
            'expectedAdmissionDate': str(self.expected_admission_date) if self.expected_admission_date else '',
            'expectedDischargeDate': str(self.expected_discharge_date) if self.expected_discharge_date else '',
            'maxStayDays': self.max_stay_days or 0,
            'surgeonId':   self.surgeon_id.id if self.surgeon_id else None,
            'surgeonName': self.surgeon_name or (self.surgeon_id.name if self.surgeon_id else ''),
            'doctorName':  self.doctor_name or self.surgeon_name or '',
            'doctorDecisionNotes': self.doctor_decision_notes or '',
            'priority': self.priority or 'عادي',
            'admissionDetails': ({
                'ward':                 self.admission_ward or '',
                'bed':                  self.admission_bed or '',
                'paymentType':          self.admission_payment_type or '',
                'attendingDoctor':      self.admission_attending_doctor or '',
                'admissionDate':        str(self.admission_date) if self.admission_date else '',
                'expectedDischargeDate': str(self.admission_expected_discharge_date) if self.admission_expected_discharge_date else '',
                'maxStayDays':          self.admission_max_stay_days or 0,
                'admissionNotes':       self.admission_notes or '',
            } if self.status == 'admitted' else None),
            'createdAt':  str(self.create_date) if self.create_date else '',
            'admittedAt': str(self.admitted_at) if self.admitted_at else None,
        }
