# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareResuscitation(models.Model):
    _name        = 'saycare.resuscitation'
    _description = 'إنعاش الطوارئ'
    _order       = 'started_at desc, id desc'
    _rec_name    = 'visit_id'

    visit_id    = fields.Many2one('saycare.visit', string='الزيارة', required=True,
                                  ondelete='cascade', index=True)
    started_at  = fields.Datetime(string='وقت الدخول للإنعاش', default=fields.Datetime.now)

    # ── بيانات القريب / المرافق ──────────────────────────────────────────────
    unknown_patient     = fields.Boolean(string='مريض مجهول الهوية')
    relative_name        = fields.Char(string='اسم المرافق / القريب')
    relative_relation     = fields.Selection([
        ('father',    'الأب'),
        ('mother',    'الأم'),
        ('spouse',    'الزوج / الزوجة'),
        ('sibling',   'الأخ / الأخت'),
        ('child',     'الابن / الابنة'),
        ('friend',    'صديق'),
        ('ambulance', 'جهة الإسعاف'),
        ('other',     'أخرى'),
    ], string='صفة القرابة')
    relative_phone       = fields.Char(string='رقم الهاتف')
    relative_alt_phone   = fields.Char(string='الرقم الموحد / الوثيقة')
    relative_address     = fields.Char(string='العنوان')
    data_source          = fields.Selection([
        ('relative',          'القريب / المرافق'),
        ('ambulance',         'الإسعاف'),
        ('police',            'الشرطة'),
        ('referral_hospital', 'مستشفى محول'),
        ('unavailable',       'غير متاح'),
    ], string='مصدر البيانات')
    relative_known_info  = fields.Text(string='بيانات المريض المتاحة من القريب')

    # ── الهوية المؤقتة ────────────────────────────────────────────────────────
    temp_name   = fields.Char(string='الاسم المؤقت')
    temp_age    = fields.Integer(string='العمر التقريبي')
    temp_gender = fields.Selection([
        ('male',    'ذكر'),
        ('female',  'أنثى'),
        ('unknown', 'غير معروف'),
    ], string='الجنس')

    # ── التقييم الفوري ABCDE ────────────────────────────────────────────────
    airway_status = fields.Selection([
        ('open',                'مفتوح'),
        ('obstructed',          'مسدود'),
        ('needs_intervention',  'يحتاج تدخل'),
    ], string='مجرى الهواء (A)')
    airway_notes = fields.Text(string='ملاحظات مجرى الهواء')

    breathing_status = fields.Selection([
        ('stable',        'مستقر'),
        ('unstable',      'غير مستقر'),
        ('needs_support', 'يحتاج دعم'),
    ], string='التنفس (B)')
    breathing_notes = fields.Text(string='ملاحظات التنفس')

    circulation_status = fields.Selection([
        ('stable',               'مستقرة'),
        ('unstable',             'غير مستقرة'),
        ('needs_intervention',   'تحتاج تدخل'),
    ], string='الدورة الدموية (C)')
    circulation_notes = fields.Text(string='ملاحظات الدورة الدموية')

    disability_status = fields.Selection([
        ('alert',        'واعٍ'),
        ('voice',        'يستجيب للصوت'),
        ('pain',         'يستجيب للألم'),
        ('unresponsive', 'غير مستجيب'),
    ], string='الوعي والعصبية (D)')
    disability_notes = fields.Text(string='ملاحظات الوعي والعصبية')

    exposure_status = fields.Selection([
        ('done',       'تم الفحص'),
        ('incomplete', 'غير مكتمل'),
        ('recheck',    'يحتاج إعادة تقييم'),
    ], string='الفحص العام (E)')
    exposure_notes = fields.Text(string='ملاحظات الفحص العام')

    # ── فريق الإنعاش ──────────────────────────────────────────────────────────
    team_lead_id     = fields.Many2one('hr.employee', string='قائد الفريق',
                                       domain=[('medical_role', '=', 'doctor')])
    resus_nurse_id   = fields.Many2one('hr.employee', string='ممرض الإنعاش',
                                       domain=[('medical_role', '=', 'nurse')])
    anesthetist_status = fields.Selection([
        ('not_requested', 'لم يُطلب'),
        ('called',        'تم الاستدعاء'),
    ], string='طبيب التخدير', default='not_requested')
    required_specialty = fields.Selection([
        ('none',        'لا يوجد'),
        ('surgery',     'جراحة'),
        ('internal',    'باطنة'),
        ('cardiology',  'قلب'),
        ('icu',         'عناية'),
    ], string='التخصص المطلوب', default='none')

    # ── التدخلات الفورية ─────────────────────────────────────────────────────
    risk_o2_support      = fields.Boolean(string='أكسجين / دعم تنفسي')
    risk_iv_line         = fields.Boolean(string='تركيب خط وريدي')
    risk_ecg             = fields.Boolean(string='رسم قلب')
    risk_urgent_labs     = fields.Boolean(string='سحب عينات عاجلة')
    risk_specialist_call = fields.Boolean(string='استدعاء تخصص')
    risk_blood_prep      = fields.Boolean(string='تجهيز مكون دم')
    intervention_notes   = fields.Text(string='تفاصيل التدخلات والأدوية المنفذة')

    vital_ids    = fields.One2many('saycare.resuscitation.vital', 'resuscitation_id',
                                   string='قراءات العلامات الحيوية')
    timeline_ids = fields.One2many('saycare.resuscitation.timeline', 'resuscitation_id',
                                   string='الخط الزمني')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('visit_uniq', 'unique(visit_id)', 'يوجد سجل إنعاش لهذه الزيارة بالفعل.'),
    ]


class SaycareResuscitationVital(models.Model):
    _name        = 'saycare.resuscitation.vital'
    _description = 'قراءة علامات حيوية أثناء الإنعاش'
    _order       = 'recorded_at desc, id desc'

    resuscitation_id = fields.Many2one('saycare.resuscitation', string='سجل الإنعاش',
                                       required=True, ondelete='cascade', index=True)
    recorded_at      = fields.Datetime(string='الوقت', default=fields.Datetime.now)
    blood_pressure   = fields.Char(string='ضغط الدم')
    pulse            = fields.Integer(string='النبض')
    temperature      = fields.Float(string='الحرارة')
    respiratory_rate = fields.Integer(string='التنفس')
    o2_saturation    = fields.Float(string='الأكسجين')
    glucose          = fields.Float(string='السكر')
    consciousness    = fields.Char(string='الوعي (A/V/P/U)')


class SaycareResuscitationTimeline(models.Model):
    _name        = 'saycare.resuscitation.timeline'
    _description = 'الخط الزمني لحالة الإنعاش'
    _order       = 'event_time desc, id desc'

    resuscitation_id = fields.Many2one('saycare.resuscitation', string='سجل الإنعاش',
                                       required=True, ondelete='cascade', index=True)
    event_time       = fields.Datetime(string='الوقت', default=fields.Datetime.now)
    message          = fields.Char(string='الحدث', required=True)
