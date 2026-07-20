# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaycareInternalDecision(models.Model):
    """شاشة قرارات الداخلي — سجل قرارات مستقل عن saycare.government.expense.decision،
    بدون أي تتبع لتوزيع شهري أو عيادات/خدمات مسموحة. مجرد بيانات القرار الأساسية
    لكل مريض."""
    _name = 'saycare.internal.decision'
    _description = 'Internal Decision (شاشة قرارات الداخلي)'
    _order = 'id desc'

    name = fields.Char('اسم القرار', required=True)
    number = fields.Char('رقم القرار')
    start_date = fields.Date('تاريخ البداية')
    duration_days = fields.Integer('مدة القرار بالأيام', default=90)
    end_date = fields.Date(
        string='تاريخ الانتهاء', compute='_compute_end_date', store=True,
    )
    total_amount = fields.Float('إجمالي المبلغ', digits=(12, 2))
    deduction_amount = fields.Float('خصم المؤسسة', digits=(12, 2), default=60.0)
    status = fields.Selection([
        ('جاري', 'جاري'),
        ('منتهي', 'منتهي'),
        ('موقوف', 'موقوف'),
    ], string='الحالة', default='جاري', required=True)
    notes = fields.Text('ملاحظات')

    # اسم المستخدم الفعلي اللى أنشأ القرار من واجهة التطبيق.
    created_by_name = fields.Char('أنشأه', copy=False)

    # رقم صفحة واحد لكل مريض — نفس فكرة saycare.government.expense.decision
    # لكن مستقلة تماماً (الفريدة بتتفحص جوه الموديل ده بس).
    page_no = fields.Integer('رقم الصفحة', copy=False)

    patient_id = fields.Many2one(
        'res.partner', string='المريض',
        domain=[('is_patient', '=', True)],
        ondelete='restrict',
    )

    distributable_amount = fields.Float(
        string='الصافي للتوزيع', digits=(12, 2), compute='_compute_distributable_amount',
    )

    @api.depends('total_amount', 'deduction_amount')
    def _compute_distributable_amount(self):
        for rec in self:
            rec.distributable_amount = round(max(0.0, rec.total_amount - rec.deduction_amount), 2)

    @api.depends('start_date', 'duration_days')
    def _compute_end_date(self):
        for rec in self:
            rec.end_date = (
                rec.start_date + timedelta(days=rec.duration_days)
                if rec.start_date and rec.duration_days
                else False
            )

    def init(self):
        self.env.cr.execute("""
            DROP INDEX IF EXISTS saycare_internal_decision_page_no_uniq
        """)

    @api.model
    def _sibling_page_no(self, patient_id):
        if patient_id:
            sibling = self.sudo().search([
                ('patient_id', '=', patient_id),
                ('page_no', '>', 0),
            ], limit=1)
            if sibling:
                return sibling.page_no
        return 0

    @api.model
    def _next_page_no(self):
        last = self.sudo().search([('page_no', '>', 0)], order='page_no desc', limit=1)
        return (last.page_no + 1) if last else 1

    @api.constrains('page_no', 'patient_id')
    def _check_page_no(self):
        for rec in self:
            if not rec.page_no:
                continue
            if rec.page_no <= 0:
                raise ValidationError('رقم الصفحة يجب أن يكون رقماً صحيحاً أكبر من صفر')
            conflict = self.sudo().search_count([
                ('page_no', '=', rec.page_no),
                ('id', '!=', rec.id),
                ('patient_id', '!=', rec.patient_id.id if rec.patient_id else False),
            ])
            if conflict:
                raise ValidationError('رقم الصفحة مستخدم بالفعل لمريض آخر')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('page_no'):
                vals['page_no'] = self._sibling_page_no(vals.get('patient_id'))
            if not vals.get('page_no'):
                raise ValidationError('رقم الصفحة مطلوب لأول قرار لهذا المريض')
        records = super().create(vals_list)
        for rec in records:
            if rec.patient_id and rec.page_no:
                siblings = self.sudo().search([
                    ('patient_id', '=', rec.patient_id.id),
                    ('id', '!=', rec.id),
                    ('page_no', '=', 0),
                ])
                if siblings:
                    siblings.write({'page_no': rec.page_no})
        return records

    def _to_dict(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'number': self.number or '',
            'startDate': str(self.start_date) if self.start_date else '',
            'durationDays': self.duration_days or 90,
            'endDate': str(self.end_date) if self.end_date else '',
            'totalAmount': self.total_amount or 0.0,
            'deductionAmount': self.deduction_amount or 0.0,
            'distributableAmount': self.distributable_amount or 0.0,
            'status': self.status or 'جاري',
            'notes': self.notes or '',
            'createdByName': self.created_by_name or self.create_uid.name or '',
            'pageNo': self.page_no if self.page_no > 0 else None,
            'patient': {
                'id': self.patient_id.id if self.patient_id else None,
                'name': self.patient_id.name or '' if self.patient_id else '',
                'mrn': self.patient_id.mrn or '' if self.patient_id else '',
                'nationalId': self.patient_id.id_number or '' if self.patient_id else '',
                'mobile': self.patient_id.phone or '' if self.patient_id else '',
            },
        }

    def _to_list_dict(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'number': self.number or '',
            'startDate': str(self.start_date) if self.start_date else '',
            'endDate': str(self.end_date) if self.end_date else '',
            'totalAmount': self.total_amount or 0.0,
            'distributableAmount': self.distributable_amount or 0.0,
            'status': self.status or 'جاري',
            'createdByName': self.created_by_name or self.create_uid.name or '',
            'pageNo': self.page_no if self.page_no > 0 else None,
            'patient': {
                'id': self.patient_id.id if self.patient_id else None,
                'name': self.patient_id.name or '' if self.patient_id else '',
                'mrn': self.patient_id.mrn or '' if self.patient_id else '',
                'nationalId': self.patient_id.id_number or '' if self.patient_id else '',
                'mobile': self.patient_id.phone or '' if self.patient_id else '',
            },
        }


class SaycareInternalDecisionServiceInvoice(models.Model):
    """فواتير الخدمات الطبية — مرتبطة بالمريض مباشرة (مش بقرار بعينه)، بتتسجل
    تلقائياً من شاشة حجز الداخلي وقت اختيار خدمات على معاملة نفقة الدولة."""
    _name = 'saycare.internal.decision.service.invoice'
    _description = 'Internal Decision - Medical Service Invoice (per patient)'
    _order = 'id desc'

    patient_id = fields.Many2one(
        'res.partner', string='المريض', required=True,
        domain=[('is_patient', '=', True)], ondelete='cascade',
    )
    invoice_number = fields.Char('رقم الفاتورة', copy=False)
    service_name = fields.Char('الخدمة', required=True)
    doctor_id = fields.Many2one(
        'hr.employee', string='الطبيب', domain=[('medical_role', '=', 'doctor')],
    )
    # Snapshot of the doctor's name at invoice time — kept even if the
    # employee record is later renamed/archived.
    doctor_name = fields.Char('اسم الدكتور')
    amount = fields.Float('المبلغ', digits=(12, 2))
    invoice_date = fields.Date('التاريخ', default=fields.Date.context_today)
    notes = fields.Text('ملاحظات')

    @api.model
    def _next_invoice_number(self):
        year = fields.Date.context_today(self).year
        count = self.sudo().search_count([('invoice_number', 'like', f'INV-{year}-%')])
        return f'INV-{year}-{count + 1:03d}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('invoice_number'):
                vals['invoice_number'] = self._next_invoice_number()
            if vals.get('doctor_id') and not vals.get('doctor_name'):
                doctor = self.env['hr.employee'].browse(int(vals['doctor_id']))
                vals['doctor_name'] = doctor.name or ''
        return super().create(vals_list)

    def _to_dict(self):
        return {
            'id': self.id,
            'patientId': self.patient_id.id if self.patient_id else None,
            'invoiceNumber': self.invoice_number or '',
            'serviceName': self.service_name or '',
            'doctorId': self.doctor_id.id if self.doctor_id else None,
            'doctorName': self.doctor_name or (self.doctor_id.name if self.doctor_id else ''),
            'amount': self.amount or 0.0,
            'date': str(self.invoice_date) if self.invoice_date else '',
            'notes': self.notes or '',
        }
