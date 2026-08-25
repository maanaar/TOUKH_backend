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

    # Structured رows for the "الطلبات" tab (lab/rad/procedure/consultation
    # orders, medications, allergies) — stored as JSON since their shape
    # mirrors the frontend's OrdersMedicationsTab form as-is, with no need
    # for per-row querying/reporting on this model.
    orders_json = fields.Text(string='بيانات الطلبات (JSON)')

    # ── التشخيص والخطة العلاجية ───────────────────────────────────────────────
    diagnosis       = fields.Text(string='التشخيص')
    treatment_plan  = fields.Text(string='الخطة العلاجية')
    treatment_given = fields.Text(string='العلاج الذي تم إعطاؤه')
    consultant_id   = fields.Many2one('hr.employee', string='الاستشاري المعالج',
                                      domain=[('medical_role', '=', 'doctor')])
    medical_advice  = fields.Text(string='الملاحظة الطبية')

    # ── الخروج إلى (نموذج كشف قسم الطوارئ) ───────────────────────────────────
    case_exit = fields.Selection([
        ('home',              'المنزل'),
        ('inpatient_dept',    'القسم الداخلي'),
        ('outpatient_clinic', 'تحويل عيادة خارجية'),
        ('other_hospital',    'تحويل مستشفى آخر'),
        ('observation',       'دخول ملاحظة'),
        ('care',              'الرعاية'),
        ('death',             'وفاة'),
    ], string='خروج الحالة')

    # ── مرفقات طبية (نموذج كشف قسم الطوارئ) ───────────────────────────────────
    sheet_no             = fields.Char(string='رقم النموذج')
    sheet_visit_type = fields.Selection([
        ('emergency',     'طارئ'),
        ('non_emergency', 'غير طارئ'),
    ], string='نوع النموذج')
    sheet_referral_party = fields.Selection([
        ('self',      'ذاتي'),
        ('ambulance', 'إسعاف'),
        ('police',    'شرطة'),
        ('hospital',  'تحويل من مستشفى آخر'),
        ('clinic',    'تحويل من عيادة'),
    ], string='الجهة')

    sheet_patient_name    = fields.Char(string='اسم المريض (النموذج)')
    sheet_age             = fields.Char(string='السن (النموذج)')
    sheet_type            = fields.Char(string='النوع (النموذج)')
    sheet_patient_card_no = fields.Char(string='رقم بطاقة المريض')
    sheet_card_no         = fields.Char(string='رقم البطاقة')
    sheet_phone           = fields.Char(string='رقم التليفون (النموذج)')
    sheet_address         = fields.Char(string='العنوان (النموذج)')
    sheet_companion       = fields.Char(string='الشخص المصاحب')
    sheet_arrival_desc    = fields.Char(string='تعريفة الوصول')
    sheet_date            = fields.Date(string='التاريخ (النموذج)')
    sheet_arrival_time    = fields.Char(string='وقت الوصول')
    sheet_departure_time  = fields.Char(string='وقت الانصراف')

    sheet_vs_pulse     = fields.Char(string='Pulse/min النبض')
    sheet_vs_temp      = fields.Char(string='Temp الحرارة')
    sheet_vs_bp        = fields.Char(string='BI/P الضغط')
    sheet_vs_rr        = fields.Char(string='R.R معدل التنفس')
    sheet_vs_allergies = fields.Char(string='Allergies حساسية')

    sheet_main_complaint         = fields.Text(string='Main Complaint')
    sheet_physical_findings      = fields.Text(string='Physical Findings')
    sheet_investigation_ordered  = fields.Text(string='Investigation Ordered')
    sheet_procedure_done         = fields.Text(string='Procedure done')
    sheet_diagnosis              = fields.Text(string='Diagnosis (النموذج)')
    sheet_treatment              = fields.Text(string='Treatment (النموذج)')

    sheet_consultant     = fields.Char(string='Consultant')
    sheet_advice_action = fields.Selection([
        ('discharged',          'خروج'),
        ('admitted',            'دخول'),
        ('referred',            'تحويل'),
        ('left_against_advice', 'انصراف تحت المسؤولية'),
    ], string='Advice action given')

    sheet_nurse_sign  = fields.Char(string='Nurse Sign')
    sheet_doctor_sign = fields.Char(string='Doctor Sign')
    sheet_cod         = fields.Char(string='Cod')

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
