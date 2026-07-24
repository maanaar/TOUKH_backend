# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareDoctorAssessment(models.Model):
    _name        = 'saycare.doctor.assessment'
    _description = 'تقييم طبيب الطوارئ'
    _order       = 'create_date desc'
    _rec_name    = 'visit_id'

    visit_id = fields.Many2one('saycare.visit', string='الزيارة', required=True,
                               ondelete='cascade', index=True)

    # ── الشكوى الرئيسية وتاريخ الحالة ────────────────────────────────────────
    chief_complaint         = fields.Char(string='الشكوى الرئيسية')
    history_present_illness = fields.Text(string='تاريخ الحالة الحالية')

    # ── الفحص السريري ────────────────────────────────────────────────────────
    general_appearance = fields.Selection([
        ('stable',   'مستقر'),
        ('unwell',   'متوعك'),
        ('critical', 'حالة حرجة'),
    ], string='المظهر العام')
    neuro_status = fields.Selection([
        ('normal',                'طبيعية'),
        ('consciousness_disorder', 'اضطراب وعي'),
        ('focal_signs',           'علامات بؤرية'),
    ], string='الحالة العصبية')
    chest_findings   = fields.Char(string='الصدر والتنفس')
    heart_findings   = fields.Char(string='القلب والدورة الدموية')
    abdomen_findings = fields.Char(string='البطن')
    limbs_findings   = fields.Char(string='الأطراف')
    exam_notes       = fields.Text(string='ملاحظات الفحص')

    # ── التاريخ المرضي SAMPLE ────────────────────────────────────────────────
    sample_signs_symptoms = fields.Text(string='الأعراض والعلامات (S)')
    sample_allergies      = fields.Text(string='الحساسية (A)')
    sample_medications    = fields.Text(string='الأدوية الحالية (M)')
    sample_past_history   = fields.Text(string='التاريخ المرضي السابق (P)')
    sample_last_intake    = fields.Text(string='آخر أكل أو شرب (L)')
    sample_events         = fields.Text(string='الأحداث المؤدية للحالة (E)')

    # ── الطلبات والفحوصات ────────────────────────────────────────────────────
    requested_tests_notes      = fields.Text(string='الفحوصات المطلوبة')
    requested_procedures_notes = fields.Text(string='الإجراءات المطلوبة')
    request_ids = fields.One2many('saycare.doctor.assessment.request', 'assessment_id',
                                  string='طلبات سريعة')

    # ── التشخيص والخطة العلاجية ───────────────────────────────────────────────
    diagnosis       = fields.Text(string='التشخيص')
    treatment_plan  = fields.Text(string='الخطة العلاجية')
    treatment_given = fields.Text(string='العلاج الذي تم إعطاؤه')
    consultant_id   = fields.Many2one('hr.employee', string='الاستشاري المعالج',
                                      domain=[('medical_role', '=', 'doctor')])
    medical_advice  = fields.Text(string='الملاحظة الطبية')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('visit_uniq', 'unique(visit_id)', 'يوجد سجل تقييم طبيب لهذه الزيارة بالفعل.'),
    ]


class SaycareDoctorAssessmentRequest(models.Model):
    _name        = 'saycare.doctor.assessment.request'
    _description = 'طلب سريع ضمن تقييم طبيب الطوارئ'
    _order       = 'id'

    assessment_id = fields.Many2one('saycare.doctor.assessment', string='التقييم',
                                    required=True, ondelete='cascade', index=True)
    name = fields.Char(string='الطلب', required=True)
