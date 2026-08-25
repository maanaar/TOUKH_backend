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

    # ── مرفقات طبية — نموذج كشف قسم الطوارئ الورقي ──────────────────────────────
    sheet_no             = fields.Char(string='رقم النموذج')
    sheet_visit_type = fields.Selection([
        ('private',   'أهلي'),
        ('ambulance', 'إسعاف'),
    ], string='النوع (أهلي/إسعاف)')
    sheet_referral_party = fields.Selection([
        ('companies', 'شركات'),
        ('police',    'شرطة'),
    ], string='الجهة (شركات/شرطة)')

    sheet_type             = fields.Char(string='النوع')
    sheet_age               = fields.Char(string='السن')
    sheet_patient_card_no   = fields.Char(string='رقم بطاقة المريض')
    sheet_address            = fields.Char(string='العنوان')
    sheet_phone              = fields.Char(string='رقم التليفون')
    sheet_arrival_desc      = fields.Char(string='تعريفة الوصول')
    sheet_date               = fields.Date(string='التاريخ')
    sheet_arrival_time      = fields.Char(string='وقت الوصول')
    sheet_card_no            = fields.Char(string='رقم البطاقة')
    sheet_companion          = fields.Char(string='الشخص المصاحب')
    sheet_departure_time    = fields.Char(string='وقت الانصراف')
    sheet_patient_name      = fields.Char(string='اسم المريض')

    sheet_vs_pulse      = fields.Char(string='النبض (Pulse/min)')
    sheet_vs_temp       = fields.Char(string='الحرارة (Temp)')
    sheet_vs_bp          = fields.Char(string='الضغط (BI/P)')
    sheet_vs_rr          = fields.Char(string='معدل التنفس (R.R)')
    sheet_vs_allergies  = fields.Char(string='حساسية (Allergies)')

    sheet_main_complaint         = fields.Text(string='شكوى المريض (Main Complaint)')
    sheet_physical_findings      = fields.Text(string='العلامات الحيوية (Physical Findings)')
    sheet_investigation_ordered = fields.Text(string='الفحوصات المطلوبة (Investigation Ordered)')
    sheet_procedure_done         = fields.Text(string='ما تم إجراؤه للمريض (Procedure done)')
    sheet_diagnosis               = fields.Text(string='التشخيص (Diagnosis)')
    sheet_treatment               = fields.Text(string='العلاج (Treatment)')
    sheet_consultant              = fields.Char(string='اسم الاستشاري المعالج (Consultant)')

    sheet_advice_action = fields.Selection([
        ('prevention',          'وقاية'),
        ('care',                'الرعاية'),
        ('hospital_admission',  'دخول مستشفى'),
        ('outpatient_transfer', 'تحويل عيادة خارجية'),
        ('internal_dept',       'القسم الداخلي'),
        ('home',                'المنزل - الخروج'),
    ], string='التصرف المتخذ (Advice action given)')

    sheet_nurse_sign  = fields.Char(string='توقيع الممرضة (Nurse Sign)')
    sheet_doctor_sign = fields.Char(string='توقيع الطبيب (Doctor Sign)')
    sheet_cod          = fields.Char(string='Cod')

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
