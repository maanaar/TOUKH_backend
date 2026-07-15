# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaycareInpatientNursingAssessment(models.Model):
    _name = 'saycare.inpatient.nursing.assessment'
    _description = 'Inpatient Nursing Receiving Assessment'
    _order = 'write_date desc, id desc'
    _rec_name = 'admission_request_id'

    _admission_request_unique = models.Constraint(
        'UNIQUE(admission_request_id)',
        'يوجد تقييم تمريضي مسجل بالفعل لهذه الحالة.',
    )

    # ── Admission link ──────────────────────────────────────────────────────

    admission_request_id = fields.Many2one(
        'saycare.admission.request',
        string='حالة الحجز الداخلي',
        required=True,
        index=True,
        ondelete='cascade',
        copy=False,
    )

    patient_id = fields.Many2one(
        'res.partner',
        string='المريض',
        related='admission_request_id.patient_id',
        store=True,
        readonly=True,
        index=True,
    )

    status = fields.Selection(
        [
            ('draft', 'مسودة'),
            ('received', 'تم استلام الحالة'),
        ],
        string='حالة التقييم',
        required=True,
        default='draft',
        index=True,
        copy=False,
    )

    # ── Receiving information ───────────────────────────────────────────────

    received_by_id = fields.Many2one(
        'hr.employee',
        string='تم الاستلام بواسطة',
        copy=False,
    )

    received_by_name = fields.Char(
        string='اسم مستلم الحالة',
        copy=False,
    )

    receiving_time = fields.Datetime(
        string='وقت الاستلام المسجل',
        default=fields.Datetime.now,
    )

    received_at = fields.Datetime(
        string='وقت تأكيد الاستلام',
        readonly=True,
        copy=False,
        index=True,
    )

    receiving_shift = fields.Selection(
        [
            ('morning', 'صباحية'),
            ('evening', 'مسائية'),
            ('night', 'ليلية'),
        ],
        string='وردية الاستلام',
    )

    bed_confirmation = fields.Selection(
        [
            ('confirmed', 'تم تأكيد السرير'),
            ('not_ready', 'السرير غير جاهز'),
            ('change_required', 'مطلوب تغيير السرير'),
            ('isolation_required', 'مطلوب سرير عزل'),
        ],
        string='تأكيد السرير',
    )

    # ── Initial nursing assessment ──────────────────────────────────────────

    consciousness = fields.Selection(
        [
            ('alert', 'واعي'),
            ('drowsy', 'نعسان'),
            ('confused', 'مشوش'),
            ('unconscious', 'فاقد الوعي'),
        ],
        string='درجة الوعي',
    )

    orientation = fields.Selection(
        [
            ('oriented', 'مدرك'),
            ('disoriented', 'غير مدرك'),
            ('partially_oriented', 'مدرك جزئياً'),
        ],
        string='الإدراك',
    )

    mobility = fields.Selection(
        [
            ('walking', 'يمشي'),
            ('assisted_walking', 'يمشي بمساعدة'),
            ('wheelchair', 'كرسي متحرك'),
            ('bedridden', 'ملازم للفراش'),
        ],
        string='الحركة',
    )

    general_condition = fields.Selection(
        [
            ('stable', 'مستقر'),
            ('unstable', 'غير مستقر'),
            ('critical', 'حرج'),
            ('immediate_review', 'يحتاج مراجعة فورية'),
        ],
        string='الحالة العامة',
    )

    pain_score = fields.Integer(
        string='درجة الألم',
    )

    weight_kg = fields.Float(
        string='الوزن كجم',
        digits=(8, 2),
    )

    height_cm = fields.Float(
        string='الطول سم',
        digits=(8, 2),
    )

    bmi = fields.Float(
        string='مؤشر كتلة الجسم',
        compute='_compute_bmi',
        store=True,
        digits=(6, 2),
    )

    requires_isolation = fields.Boolean(
        string='يحتاج عزل',
        default=False,
    )

    oxygen_required = fields.Boolean(
        string='يحتاج أكسجين',
        default=False,
    )

    npo = fields.Boolean(
        string='ممنوع الأكل والشرب',
        default=False,
    )

    high_dependency = fields.Boolean(
        string='رعاية عالية الاعتماد',
        default=False,
    )

    doctor_to_be_notified = fields.Boolean(
        string='يجب إخطار الطبيب',
        default=False,
    )

    # ── Initial vital signs ─────────────────────────────────────────────────

    temperature_c = fields.Float(
        string='درجة الحرارة',
        digits=(5, 2),
    )

    pulse_bpm = fields.Integer(
        string='النبض',
    )

    blood_pressure = fields.Char(
        string='ضغط الدم',
    )

    respiratory_rate = fields.Integer(
        string='معدل التنفس',
    )

    spo2_percent = fields.Float(
        string='تشبع الأكسجين',
        digits=(5, 2),
    )

    blood_glucose = fields.Float(
        string='سكر الدم',
        digits=(8, 2),
    )

    vital_pain_score = fields.Integer(
        string='درجة الألم مع العلامات الحيوية',
    )

    vitals_recorded_by_name = fields.Char(
        string='مسجل العلامات الحيوية',
    )

    # ── Allergies ───────────────────────────────────────────────────────────

    drug_allergy = fields.Char(
        string='حساسية الأدوية',
    )

    food_allergy = fields.Char(
        string='حساسية الطعام',
    )

    latex_allergy = fields.Selection(
        [
            ('no', 'لا'),
            ('yes', 'نعم'),
            ('unknown', 'غير معروف'),
        ],
        string='حساسية اللاتكس',
    )

    allergy_status = fields.Selection(
        [
            ('no_known_allergy', 'لا توجد حساسية معروفة'),
            ('known_allergy', 'توجد حساسية معروفة'),
            ('unknown', 'غير معروف'),
        ],
        string='حالة الحساسية',
    )

    # ── Infection control ───────────────────────────────────────────────────

    isolation_type = fields.Selection(
        [
            ('none', 'بدون عزل'),
            ('contact', 'عزل تلامس'),
            ('droplet', 'عزل رذاذ'),
            ('airborne', 'عزل هوائي'),
            ('protective', 'عزل وقائي'),
        ],
        string='نوع العزل',
    )

    infection_risk = fields.Selection(
        [
            ('low', 'منخفض'),
            ('medium', 'متوسط'),
            ('high', 'مرتفع'),
        ],
        string='خطورة العدوى',
    )

    ppe_required = fields.Selection(
        [
            ('standard', 'احتياطات قياسية'),
            ('gloves', 'قفازات'),
            ('mask', 'كمامة'),
            ('gown', 'رداء واقٍ'),
            ('full_ppe', 'معدات وقاية كاملة'),
        ],
        string='معدات الوقاية المطلوبة',
    )

    infection_notes = fields.Text(
        string='ملاحظات مكافحة العدوى',
    )

    # ── Risk assessment ─────────────────────────────────────────────────────

    fall_risk = fields.Selection(
        [
            ('low', 'منخفض'),
            ('medium', 'متوسط'),
            ('high', 'مرتفع'),
        ],
        string='خطر السقوط',
    )

    braden_scale_score = fields.Integer(
        string='درجة مقياس برادن',
    )

    pressure_ulcer_risk = fields.Selection(
        [
            ('no_risk', 'لا توجد خطورة'),
            ('low', 'منخفضة'),
            ('moderate', 'متوسطة'),
            ('high', 'مرتفعة'),
        ],
        string='خطر قرح الفراش',
    )

    nutrition_risk = fields.Selection(
        [
            ('low', 'منخفض'),
            ('medium', 'متوسط'),
            ('high', 'مرتفع'),
        ],
        string='خطر سوء التغذية',
    )

    psychological_safety_risk = fields.Selection(
        [
            ('not_assessed', 'لم يتم التقييم'),
            ('no_risk', 'لا توجد خطورة ملحوظة'),
            ('needs_review', 'يحتاج مراجعة'),
            ('urgent_review', 'يحتاج مراجعة نفسية عاجلة'),
        ],
        string='خطر السلامة النفسية',
    )

    dvt_risk = fields.Selection(
        [
            ('low', 'منخفض'),
            ('medium', 'متوسط'),
            ('high', 'مرتفع'),
        ],
        string='خطر الجلطات الوريدية',
    )

    bleeding_risk = fields.Selection(
        [
            ('low', 'منخفض'),
            ('medium', 'متوسط'),
            ('high', 'مرتفع'),
        ],
        string='خطر النزيف',
    )

    risk_action = fields.Char(
        string='إجراء التمريض المطلوب',
    )

    # ── Patient belongings ──────────────────────────────────────────────────

    belonging_mobile = fields.Boolean(
        string='هاتف محمول',
        default=False,
    )

    belonging_money = fields.Boolean(
        string='أموال',
        default=False,
    )

    belonging_watch = fields.Boolean(
        string='ساعة',
        default=False,
    )

    belonging_clothes = fields.Boolean(
        string='ملابس',
        default=False,
    )

    belonging_documents = fields.Boolean(
        string='مستندات',
        default=False,
    )

    belonging_glasses = fields.Boolean(
        string='نظارة',
        default=False,
    )

    belonging_denture = fields.Boolean(
        string='طقم أسنان',
        default=False,
    )

    belonging_other = fields.Boolean(
        string='متعلقات أخرى',
        default=False,
    )

    belongings_handed_to = fields.Char(
        string='تم تسليم المتعلقات إلى',
    )

    belongings_relative_name = fields.Char(
        string='اسم المستلم',
    )

    belongings_signature_or_id = fields.Char(
        string='التوقيع أو رقم الهوية',
    )

    # ── IV access / lines / drains ──────────────────────────────────────────

    cannula_status = fields.Selection(
        [
            ('no', 'لا'),
            ('yes', 'نعم'),
        ],
        string='كانولا',
    )

    cannula_site = fields.Selection(
        [
            ('right_hand', 'اليد اليمنى'),
            ('left_hand', 'اليد اليسرى'),
            ('right_arm', 'الذراع اليمنى'),
            ('left_arm', 'الذراع اليسرى'),
            ('other', 'أخرى'),
        ],
        string='مكان الكانولا',
    )

    cannula_size = fields.Selection(
        [
            ('18g', '18G'),
            ('20g', '20G'),
            ('22g', '22G'),
            ('24g', '24G'),
        ],
        string='مقاس الكانولا',
    )

    cannula_insertion_date = fields.Datetime(
        string='تاريخ تركيب الكانولا',
    )

    urinary_catheter_status = fields.Selection(
        [
            ('no', 'لا'),
            ('yes', 'نعم'),
        ],
        string='قسطرة بولية',
    )

    ng_tube_status = fields.Selection(
        [
            ('no', 'لا'),
            ('yes', 'نعم'),
        ],
        string='أنبوب أنفي معدي',
    )

    drain_status = fields.Selection(
        [
            ('no', 'لا'),
            ('yes', 'نعم'),
        ],
        string='مصرف',
    )

    drain_type_site = fields.Char(
        string='نوع أو مكان المصرف',
    )

    # ── Notes ────────────────────────────────────────────────────────────────

    nursing_notes = fields.Text(
        string='ملاحظات التمريض عند الاستلام',
    )

    @api.depends('weight_kg', 'height_cm')
    def _compute_bmi(self):
        for rec in self:
            height_m = (rec.height_cm or 0.0) / 100.0
            if rec.weight_kg > 0 and height_m > 0:
                rec.bmi = rec.weight_kg / (height_m * height_m)
            else:
                rec.bmi = 0.0