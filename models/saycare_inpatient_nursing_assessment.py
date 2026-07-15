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

    # ── Vital signs monitoring chart (نموذج العلامات الحيوية) ───────────────

    vsc_date = fields.Date(
        string='تاريخ تسجيل العلامات الحيوية',
    )

    vsc_time = fields.Char(
        string='ساعة تسجيل العلامات الحيوية',
    )

    vsc_pulse = fields.Integer(
        string='النبض',
    )

    vsc_blood_pressure = fields.Char(
        string='ضغط الدم',
    )

    vsc_temperature = fields.Float(
        string='درجة الحرارة',
        digits=(5, 2),
    )

    vsc_respiration = fields.Integer(
        string='التنفس',
    )

    vsc_score = fields.Integer(
        string='الدرجة (النتيجة الإجمالية)',
    )

    vsc_notes = fields.Text(
        string='ملاحظات العلامات الحيوية',
    )

    vsc_signature_id = fields.Many2one(
        'hr.employee',
        string='توقيع (العلامات الحيوية)',
    )

    # ── Once-only medication prescription & administration ──────────────────

    once_med_doctor_id = fields.Many2one(
        'hr.employee',
        string='الطبيب المعالج',
    )

    once_med_diagnosis = fields.Char(
        string='التشخيص',
    )

    once_med_date = fields.Date(
        string='تاريخ إعطاء العلاج',
    )

    once_med_time = fields.Char(
        string='وقت إعطاء العلاج',
    )

    once_med_name = fields.Char(
        string='اسم الدواء وتركيزه',
    )

    once_med_form = fields.Selection(
        [
            ('tablet', 'أقراص'),
            ('capsule', 'كبسولات'),
            ('injection', 'حقن'),
            ('syrup', 'شراب'),
            ('ampoule', 'أمبولات'),
            ('suppository', 'تحاميل'),
            ('cream', 'كريم'),
            ('drops', 'قطرات'),
            ('inhaler', 'بخاخ'),
            ('other', 'أخرى'),
        ],
        string='الشكل الدوائي',
    )

    once_med_dosage = fields.Char(
        string='الجرعة/التكرار/المدة',
    )

    once_med_route = fields.Selection(
        [
            ('oral', 'فموي'),
            ('iv', 'وريدي'),
            ('im', 'عضلي'),
            ('sc', 'تحت الجلد'),
            ('sublingual', 'تحت اللسان'),
            ('topical', 'موضعي'),
            ('rectal', 'شرجي'),
            ('inhalation', 'استنشاق'),
            ('other', 'أخرى'),
        ],
        string='طريقة الإعطاء',
    )

    once_med_instructions = fields.Text(
        string='تعليمات الدواء',
    )

    once_med_pharmacist_id = fields.Many2one(
        'hr.employee',
        string='توقيع الصيدلي',
    )

    once_med_admin_time = fields.Char(
        string='وقت الإعطاء',
    )

    once_med_nurse_id = fields.Many2one(
        'hr.employee',
        string='توقيع الممرضة (وصف وإعطاء علاج مرة واحدة)',
    )

    # ── Fluid balance (خريطة السوائل) ────────────────────────────────────────

    fluid_balance_diagnosis = fields.Char(
        string='التشخيص (ICD-11)',
    )

    fluid_balance_date = fields.Date(
        string='تاريخ ميزان السوائل',
    )

    fluid_balance_nurse_id = fields.Many2one(
        'hr.employee',
        string='توقيع التمريض (ميزان السوائل)',
    )

    fluid_balance_oral_intake = fields.Float(
        string='إجمالي السوائل الداخلة بالفم',
        digits=(8, 2),
    )

    fluid_balance_iv_intake = fields.Float(
        string='إجمالي السوائل الداخلة بالوريد',
        digits=(8, 2),
    )

    fluid_balance_total_intake = fields.Float(
        string='إجمالي السوائل الداخلة',
        compute='_compute_fluid_balance',
        store=True,
        digits=(8, 2),
    )

    fluid_balance_urine_output = fields.Float(
        string='إجمالي البول',
        digits=(8, 2),
    )

    fluid_balance_drain_output = fields.Float(
        string='إجمالي الدرنقة',
        digits=(8, 2),
    )

    fluid_balance_total_output = fields.Float(
        string='إجمالي السوائل الخارجة',
        compute='_compute_fluid_balance',
        store=True,
        digits=(8, 2),
    )

    fluid_balance_result = fields.Float(
        string='توازن السوائل',
        compute='_compute_fluid_balance',
        store=True,
        digits=(8, 2),
    )

    # ── IV fluids infusion (وصف وإعطاء محاليل وريدية) ────────────────────────

    iv_infusion_datetime = fields.Datetime(
        string='تاريخ وساعة وصف المحلول',
    )

    iv_infusion_solution_name = fields.Char(
        string='اسم المحلول',
    )

    iv_infusion_volume = fields.Float(
        string='حجم المحلول',
        digits=(8, 2),
    )

    iv_infusion_additives = fields.Char(
        string='الإضافات',
    )

    iv_infusion_rate = fields.Char(
        string='المعدل',
    )

    iv_infusion_line = fields.Char(
        string='اللاين',
    )

    iv_infusion_instructions = fields.Text(
        string='تعليمات المحلول',
    )

    iv_infusion_doctor_id = fields.Many2one(
        'hr.employee',
        string='توقيع الطبيب (المحاليل الوريدية)',
    )

    iv_infusion_pharmacist_id = fields.Many2one(
        'hr.employee',
        string='توقيع الصيدلي (المحاليل الوريدية)',
    )

    iv_infusion_admin_datetime = fields.Datetime(
        string='تاريخ ووقت إعطاء المحلول',
    )

    iv_infusion_admin_volume = fields.Float(
        string='الحجم المعطى',
        digits=(8, 2),
    )

    iv_infusion_nurse_id = fields.Many2one(
        'hr.employee',
        string='توقيع الممرضة (المحاليل الوريدية)',
    )

    @api.depends('weight_kg', 'height_cm')
    def _compute_bmi(self):
        for rec in self:
            height_m = (rec.height_cm or 0.0) / 100.0
            if rec.weight_kg > 0 and height_m > 0:
                rec.bmi = rec.weight_kg / (height_m * height_m)
            else:
                rec.bmi = 0.0

    @api.depends(
        'fluid_balance_oral_intake', 'fluid_balance_iv_intake',
        'fluid_balance_urine_output', 'fluid_balance_drain_output',
    )
    def _compute_fluid_balance(self):
        for rec in self:
            rec.fluid_balance_total_intake = (
                rec.fluid_balance_oral_intake + rec.fluid_balance_iv_intake
            )
            rec.fluid_balance_total_output = (
                rec.fluid_balance_urine_output + rec.fluid_balance_drain_output
            )
            rec.fluid_balance_result = (
                rec.fluid_balance_total_intake - rec.fluid_balance_total_output
            )