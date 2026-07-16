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

    department_id = fields.Many2one(
        'hospital.inpatient.department',
        string='القسم',
        related='admission_request_id.department_id',
        store=True,
        readonly=True,
    )

    admission_date = fields.Date(
        string='تاريخ الدخول',
        related='admission_request_id.admission_date',
        store=True,
        readonly=True,
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

    # ── Blood glucose / insulin monitoring (متابعة قياس نسبة السكر) ─────────

    bg_diagnosis = fields.Char(
        string='التشخيص (متابعة السكر)',
    )

    bg_date = fields.Date(
        string='تاريخ قياس السكر',
    )

    bg_time = fields.Char(
        string='وقت قياس السكر',
    )

    bg_level = fields.Float(
        string='نسبة سكر الدم',
        digits=(6, 2),
    )

    bg_oral = fields.Boolean(
        string='بالفم (Oral)',
        default=False,
    )

    bg_insulin_type = fields.Char(
        string='نوع الأنسولين',
    )

    bg_dose_units = fields.Float(
        string='الجرعة (وحدات)',
        digits=(6, 2),
    )

    bg_route = fields.Selection(
        [
            ('sc', 'تحت الجلد'),
            ('iv', 'وريدي'),
            ('im', 'عضلي'),
            ('other', 'أخرى'),
        ],
        string='طريقة الإعطاء',
    )

    bg_site = fields.Selection(
        [
            ('front_right_arm', 'الذراع الأيمن (أمامي)'),
            ('front_left_arm', 'الذراع الأيسر (أمامي)'),
            ('abdomen_upper_right', 'أعلى يمين البطن'),
            ('abdomen_upper_left', 'أعلى يسار البطن'),
            ('abdomen_lower_right', 'أسفل يمين البطن'),
            ('abdomen_lower_left', 'أسفل يسار البطن'),
            ('front_right_thigh', 'الفخذ الأيمن (أمامي)'),
            ('front_left_thigh', 'الفخذ الأيسر (أمامي)'),
            ('back_right_arm', 'الذراع الأيمن (خلفي)'),
            ('back_left_arm', 'الذراع الأيسر (خلفي)'),
            ('back_right_hip', 'الأرداف/الفخذ الأيمن (خلفي)'),
            ('back_left_hip', 'الأرداف/الفخذ الأيسر (خلفي)'),
        ],
        string='المكان (موقع الحقن)',
    )

    bg_urine_acetone = fields.Selection(
        [
            ('negative', 'سلبي'),
            ('trace', 'أثر'),
            ('small', 'بسيط (+1)'),
            ('moderate', 'متوسط (+2)'),
            ('large', 'كبير (+3)'),
        ],
        string='الأسيتون في البول',
    )

    bg_signature_id = fields.Many2one(
        'hr.employee',
        string='التوقيع (متابعة السكر)',
    )

    bg_notes = fields.Text(
        string='ملاحظات متابعة السكر',
    )

    # ── ICU lab results flow sheet ───────────────────────────────────────────

    icu_lab_date = fields.Date(
        string='تاريخ نتائج المعمل',
    )

    icu_lab_wbc = fields.Float(string='WBCs', digits=(8, 2))
    icu_lab_rbc = fields.Float(string='RBCs', digits=(8, 2))
    icu_lab_hb = fields.Float(string='Hb (gm%)', digits=(8, 2))
    icu_lab_hct = fields.Float(string='Hct (%)', digits=(8, 2))
    icu_lab_platelets = fields.Float(string='Platelets', digits=(8, 2))

    icu_lab_pt = fields.Float(string='PT', digits=(8, 2))
    icu_lab_pc = fields.Float(string='PC', digits=(8, 2))
    icu_lab_inr = fields.Float(string='INR', digits=(8, 2))
    icu_lab_ptt = fields.Float(string='PTT', digits=(8, 2))

    icu_lab_total_protein = fields.Float(string='Total Protein', digits=(8, 2))
    icu_lab_albumin = fields.Float(string='Albumin (mg%)', digits=(8, 2))
    icu_lab_t_bilirubin = fields.Float(string='T. Bilirubin', digits=(8, 2))
    icu_lab_d_bilirubin = fields.Float(string='D. Bilirubin', digits=(8, 2))
    icu_lab_alt_sgpt = fields.Float(string='ALT (SGPT)', digits=(8, 2))
    icu_lab_ast_sgot = fields.Float(string='AST (SGOT)', digits=(8, 2))
    icu_lab_alp = fields.Float(string='ALP', digits=(8, 2))

    icu_lab_urea = fields.Float(string='Urea', digits=(8, 2))
    icu_lab_creatinine = fields.Float(string='Creat (mg%)', digits=(8, 2))
    icu_lab_uric_acid = fields.Float(string='Uric Acid (mg)', digits=(8, 2))

    icu_lab_na = fields.Float(string='Na+ (meq/l)', digits=(8, 2))
    icu_lab_k = fields.Float(string='K+ (meq/l)', digits=(8, 2))
    icu_lab_ca = fields.Float(string='Ca++', digits=(8, 2))
    icu_lab_mg = fields.Float(string='Mg++', digits=(8, 2))
    icu_lab_po4 = fields.Float(string='PO4', digits=(8, 2))

    icu_lab_cpk = fields.Float(string='CPK', digits=(8, 2))
    icu_lab_cpk_mb = fields.Float(string='CPK-MB', digits=(8, 2))
    icu_lab_ldh = fields.Float(string='LDH', digits=(8, 2))
    icu_lab_troponin = fields.Float(string='Troponin', digits=(8, 2))

    icu_lab_cholesterol = fields.Float(string='Cholesterol', digits=(8, 2))
    icu_lab_triglycerides = fields.Float(string='Triglycerides', digits=(8, 2))
    icu_lab_ldl = fields.Float(string='LDL', digits=(8, 2))
    icu_lab_hdl = fields.Float(string='HDL', digits=(8, 2))

    icu_lab_ph = fields.Float(string='pH', digits=(4, 2))
    icu_lab_pco2 = fields.Float(string='PCO2', digits=(8, 2))
    icu_lab_o2_sat = fields.Float(string='O2 Sat', digits=(8, 2))
    icu_lab_hco3 = fields.Float(string='HCO3', digits=(8, 2))

    icu_lab_other_notes = fields.Text(
        string='نتائج معملية أخرى / ملاحظات',
    )

    # ── Pressure ulcer follow up (متابعة قرح الفراش) ─────────────────────────

    pu_discovery_date = fields.Date(
        string='تاريخ اكتشاف القرحة',
    )

    pu_location = fields.Selection(
        [
            ('head', 'الرأس'),
            ('shoulder', 'الكتف'),
            ('sacrum', 'العجز (أسفل الظهر)'),
            ('buttock', 'الأرداف'),
            ('heel', 'الكعب'),
            ('other', 'أخرى'),
        ],
        string='مكان القرحة',
    )

    pu_grade = fields.Selection(
        [
            ('stage1', 'المرحلة الأولى (احمرار الجلد)'),
            ('stage2', 'المرحلة الثانية (إصابة الجلد)'),
            ('stage3', 'المرحلة الثالثة (امتداد الإصابة حتى الطبقة الثانية والأنسجة)'),
            ('stage4', 'المرحلة الرابعة (إصابة الجلد والأنسجة وصولاً للعظم)'),
        ],
        string='درجة القرحة',
    )

    pu_position = fields.Selection(
        [
            ('front', 'الوضع الأمامي (على البطن)'),
            ('back', 'الوضع الخلفي (على الظهر)'),
            ('semi_sitting', 'نصف جالس'),
            ('right_side', 'النوم على الجانب الأيمن'),
            ('left_side', 'النوم على الجانب الأيسر'),
        ],
        string='وضعية نوم المريض',
    )

    pu_nurse_id = fields.Many2one(
        'hr.employee',
        string='توقيع التمريض (متابعة قرح الفراش)',
    )

    pu_turning_chart_placed = fields.Boolean(
        string='وضع نموذج خريطة التقليب',
        default=False,
    )

    pu_pressure_avoided = fields.Boolean(
        string='عدم الضغط على منطقة القرحة',
        default=False,
    )

    pu_area_clean_dry = fields.Boolean(
        string='المحافظة على مكان القرحة نظيف وجاف',
        default=False,
    )

    pu_air_mattress = fields.Boolean(
        string='وضع مرتبة هوائية',
        default=False,
    )

    pu_wound_cleaned_saline = fields.Boolean(
        string='تنظيف الجرح بمحلول ملح وتجفيفه جيداً',
        default=False,
    )

    pu_antibiotic_used = fields.Boolean(
        string='استعمال مضاد حيوي (حسب أوامر الطبيب)',
        default=False,
    )

    pu_sterile_gauze_changed = fields.Boolean(
        string='وضع شاش معقم يتغير مرتين يومياً',
        default=False,
    )

    pu_color_notes = fields.Char(
        string='لون القرحة',
    )

    pu_discharge_type = fields.Char(
        string='نوع الإفرازات',
    )

    pu_infection_signs_reported = fields.Boolean(
        string='تم إبلاغ الطبيب بعلامات العدوى',
        default=False,
    )

    pu_care_plan = fields.Text(
        string='خطة الرعاية التمريضية',
    )

    pu_repositioning_education = fields.Boolean(
        string='تثقيف المريض/الأهل لتجنب قرح الفراش',
        default=False,
    )

    # ── Pain measurement & treatment (قياس الألم وعلاجه) ─────────────────────

    pmt_date = fields.Date(
        string='تاريخ قياس الألم',
    )

    pmt_age = fields.Integer(
        string='السن (قياس الألم)',
    )

    pmt_time = fields.Char(
        string='الوقت (قياس الألم)',
    )

    pmt_scale_method = fields.Selection(
        [
            ('numerical', '(A) مقياس رقمي لحدة الألم - للبالغين والمرضى الواعين'),
            ('wong_baker', '(B) مقياس الوجوه Wong-Baker لحدة الألم'),
        ],
        string='طريقة قياس الألم',
    )

    pmt_pain_measure = fields.Selection(
        [
            ('0', '0 - لا ألم (No Pain)'),
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5 - ألم متوسط (Moderate Pain)'),
            ('6', '6'),
            ('7', '7'),
            ('8', '8'),
            ('9', '9'),
            ('10', '10 - أشد الألم (Worst Possible Pain)'),
        ],
        string='مقياس الألم',
    )

    pmt_pain_location = fields.Selection(
        [
            ('right', 'يمين (Right)'),
            ('left', 'يسار (Left)'),
            ('both', 'الاثنان (Both)'),
        ],
        string='مكان الألم',
    )

    pmt_pain_type = fields.Selection(
        [
            ('aching', 'موجع (Aching)'),
            ('burning', 'محرق (Burning)'),
            ('cramping', 'تقلص (Cramping)'),
            ('crushing', 'سحق (Crushing)'),
            ('dull', 'كليل (Dull)'),
            ('numbness', 'تنميل (Numbness)'),
            ('pins_needles', 'وخز (Pins / Needles)'),
            ('stabbing', 'طعن (Stabbing)'),
            ('throbbing', 'نابض (Throbbing)'),
        ],
        string='نوع الألم',
    )

    pmt_intervention_type = fields.Selection(
        [
            ('1', '1 = إجراء تداخلي لعلاج الألم (Intervention Pain Relief Procedure)'),
            ('2', '2 = دوائي (Pharmacological - See Medication Sheet)'),
            ('3', '3 = بدون أدوية (Non-pharmacological)'),
        ],
        string='التدخل العلاجي',
    )

    pmt_nonpharm_method = fields.Selection(
        [
            ('a', 'A - تغيير الوضع (Position Changed)'),
            ('b', 'B - محاولة الاسترخاء (Relaxation Technique)'),
            ('c', 'C - تدعيم (Splinting)'),
            ('d', 'D - شد الانتباه (Distractions)'),
            ('e', 'E - الموسيقى (Music)'),
            ('f', 'F - تعليم السيطرة على الألم (Education)'),
            ('g', 'G - أخرى (Others)'),
        ],
        string='طريقة العلاج بدون أدوية',
    )

    pmt_nonpharm_other_specify = fields.Char(
        string='تحديد طريقة العلاج الأخرى',
    )

    pmt_nurse_signature_id = fields.Many2one(
        'hr.employee',
        string='توقيع التمريض (قياس الألم)',
    )

    pmt_notes = fields.Text(
        string='ملاحظات (قياس الألم)',
    )

    # ── Nurse observation sheet (ملاحظة ممرضة) ───────────────────────────────

    nurse_obs_admission_permit_no = fields.Char(
        string='إذن قبول رقم',
    )

    nurse_obs_referred_from = fields.Char(
        string='مرسل من',
    )

    nurse_obs_diagnosis = fields.Char(
        string='التشخيص (ملاحظة ممرضة)',
    )

    nurse_obs_specialist_id = fields.Many2one(
        'hr.employee',
        string='اسم الاخصائي',
    )

    nurse_obs_date = fields.Date(
        string='التاريخ (ملاحظة ممرضة)',
    )

    nurse_obs_time = fields.Char(
        string='الساعة (ملاحظة ممرضة)',
    )

    nurse_obs_note = fields.Text(
        string='ملاحظة المريض',
    )

    nurse_obs_signature_id = fields.Many2one(
        'hr.employee',
        string='الامضاء (ملاحظة ممرضة)',
    )

    # ── Nursing care plan (خطة الرعاية التمريضية) ────────────────────────────

    care_plan_datetime = fields.Datetime(
        string='الوقت/التاريخ (خطة الرعاية)',
    )

    care_plan_nursing_diagnosis = fields.Text(
        string='التشخيص التمريضي',
    )

    care_plan_patient_needs = fields.Text(
        string='احتياجات المريض',
    )

    care_plan_actions = fields.Text(
        string='الإجراءات',
    )

    care_plan_expected_outcomes = fields.Text(
        string='النتائج المرجوة',
    )

    care_plan_time_frame = fields.Char(
        string='الأطار الزمني',
    )

    care_plan_signature_id = fields.Many2one(
        'hr.employee',
        string='التوقيع (خطة الرعاية التمريضية)',
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