# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaycareInpatientNursingSheetEntryMixin(models.AbstractModel):
    _name = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _description = 'Inpatient Nursing Sheet Entry Mixin'

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

    recorded_by_id = fields.Many2one(
        'hr.employee',
        string='تم التسجيل بواسطة',
        readonly=True,
        copy=False,
        index=True,
    )

    recorded_by_name = fields.Char(
        string='اسم المسجل',
        readonly=True,
        copy=False,
    )

    recorded_at = fields.Datetime(
        string='وقت التسجيل',
        required=True,
        default=fields.Datetime.now,
        copy=False,
        index=True,
    )

    def _check_non_negative(self, field_labels):
        for record in self:
            for field_name, label in field_labels:
                value = record[field_name]
                if value is not False and value < 0:
                    raise ValidationError(
                        f'{label} لا يمكن أن يكون قيمة سالبة'
                    )


class SaycareInpatientNursingVitalEntry(models.Model):
    _name = 'saycare.inpatient.nursing.vital.entry'
    _description = 'Inpatient Nursing Vital Signs Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'entry_date'

    entry_date = fields.Date(string='التاريخ', required=True, index=True)
    entry_time = fields.Char(string='الساعة')
    pulse = fields.Integer(string='النبض')
    blood_pressure = fields.Char(string='ضغط الدم')
    temperature = fields.Float(string='درجة الحرارة', digits=(5, 2))
    respiration = fields.Integer(string='التنفس')
    score = fields.Integer(string='الدرجة (النتيجة الإجمالية)')
    notes = fields.Text(string='ملاحظات العلامات الحيوية')

    @api.constrains('pulse', 'temperature', 'respiration', 'score')
    def _check_numeric_values(self):
        self._check_non_negative([
            ('pulse', 'النبض'),
            ('temperature', 'درجة الحرارة'),
            ('respiration', 'التنفس'),
            ('score', 'الدرجة'),
        ])


class SaycareInpatientNursingPainEntry(models.Model):
    _name = 'saycare.inpatient.nursing.pain.entry'
    _description = 'Inpatient Nursing Pain Measurement Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'entry_date'

    entry_date = fields.Date(string='تاريخ قياس الألم', required=True, index=True)
    age = fields.Integer(string='السن')
    entry_time = fields.Char(string='الوقت')

    scale_method = fields.Selection([
        ('numerical', '(A) مقياس رقمي لحدة الألم'),
        ('wong_baker', '(B) مقياس الوجوه Wong-Baker'),
    ], string='طريقة قياس الألم')

    pain_measure = fields.Selection([
        ('0', '0 - لا ألم'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5 - ألم متوسط'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10 - أشد الألم'),
    ], string='مقياس الألم')

    pain_location = fields.Selection([
        ('right', 'يمين'),
        ('left', 'يسار'),
        ('both', 'الاثنان'),
    ], string='مكان الألم')

    pain_type = fields.Selection([
        ('aching', 'موجع'),
        ('burning', 'محرق'),
        ('cramping', 'تقلص'),
        ('crushing', 'سحق'),
        ('dull', 'كليل'),
        ('numbness', 'تنميل'),
        ('pins_needles', 'وخز'),
        ('stabbing', 'طعن'),
        ('throbbing', 'نابض'),
    ], string='نوع الألم')

    intervention_type = fields.Selection([
        ('1', 'إجراء تداخلي لعلاج الألم'),
        ('2', 'دوائي'),
        ('3', 'بدون أدوية'),
    ], string='التدخل العلاجي')

    nonpharm_method = fields.Selection([
        ('a', 'تغيير الوضع'),
        ('b', 'محاولة الاسترخاء'),
        ('c', 'تدعيم'),
        ('d', 'شد الانتباه'),
        ('e', 'الموسيقى'),
        ('f', 'تعليم السيطرة على الألم'),
        ('g', 'أخرى'),
    ], string='طريقة العلاج بدون أدوية')

    nonpharm_other_specify = fields.Char(
        string='تحديد طريقة العلاج الأخرى'
    )
    notes = fields.Text(string='ملاحظات قياس الألم')

    @api.constrains('age')
    def _check_age(self):
        self._check_non_negative([('age', 'السن')])


class SaycareInpatientNursingObservationEntry(models.Model):
    _name = 'saycare.inpatient.nursing.observation.entry'
    _description = 'Inpatient Nurse Observation Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'entry_date'

    admission_permit_no = fields.Char(string='إذن قبول رقم')
    referred_from = fields.Char(string='مرسل من')
    diagnosis = fields.Char(string='التشخيص')
    specialist_name = fields.Char(string='اسم الأخصائي')
    entry_date = fields.Date(string='التاريخ', required=True, index=True)
    entry_time = fields.Char(string='الساعة')
    note = fields.Text(string='ملاحظة المريض')


class SaycareInpatientNursingCarePlanEntry(models.Model):
    _name = 'saycare.inpatient.nursing.care.plan.entry'
    _description = 'Inpatient Nursing Care Plan Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_datetime desc, id desc'
    _rec_name = 'entry_datetime'

    entry_datetime = fields.Datetime(
        string='الوقت والتاريخ',
        required=True,
        index=True,
    )
    nursing_diagnosis = fields.Text(string='التشخيص التمريضي')
    patient_needs = fields.Text(string='احتياجات المريض')
    actions = fields.Text(string='الإجراءات')
    expected_outcomes = fields.Text(string='النتائج المرجوة')
    time_frame = fields.Char(string='الإطار الزمني')


class SaycareInpatientNursingOnceMedicationEntry(models.Model):
    _name = 'saycare.inpatient.nursing.once.medication.entry'
    _description = 'Inpatient Once-only Medication Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'medication_name'

    doctor_name = fields.Char(string='الطبيب المعالج')
    diagnosis = fields.Char(string='التشخيص')
    entry_date = fields.Date(string='تاريخ إعطاء العلاج', index=True)
    entry_time = fields.Char(string='وقت وصف العلاج')
    medication_name = fields.Char(
        string='اسم الدواء وتركيزه',
        required=True,
    )
    medication_form = fields.Selection([
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
    ], string='الشكل الدوائي')
    dosage = fields.Char(string='الجرعة والتكرار والمدة')
    route = fields.Selection([
        ('oral', 'فموي'),
        ('iv', 'وريدي'),
        ('im', 'عضلي'),
        ('sc', 'تحت الجلد'),
        ('sublingual', 'تحت اللسان'),
        ('topical', 'موضعي'),
        ('rectal', 'شرجي'),
        ('inhalation', 'استنشاق'),
        ('other', 'أخرى'),
    ], string='طريقة الإعطاء')
    instructions = fields.Text(string='تعليمات الدواء')
    pharmacist_name = fields.Char(string='الصيدلي')
    administration_time = fields.Char(string='وقت الإعطاء')


class SaycareInpatientNursingIvInfusionEntry(models.Model):
    _name = 'saycare.inpatient.nursing.iv.infusion.entry'
    _description = 'Inpatient IV Infusion Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'prescribed_datetime desc, id desc'
    _rec_name = 'solution_name'

    prescribed_datetime = fields.Datetime(
        string='تاريخ وساعة وصف المحلول',
        index=True,
    )
    solution_name = fields.Char(string='اسم المحلول', required=True)
    volume = fields.Float(string='حجم المحلول', digits=(8, 2))
    additives = fields.Char(string='الإضافات')
    rate = fields.Char(string='المعدل')
    line = fields.Char(string='اللاين')
    instructions = fields.Text(string='تعليمات المحلول')
    doctor_name = fields.Char(string='الطبيب')
    pharmacist_name = fields.Char(string='الصيدلي')
    administered_datetime = fields.Datetime(
        string='تاريخ ووقت إعطاء المحلول',
        index=True,
    )
    administered_volume = fields.Float(
        string='الحجم المعطى',
        digits=(8, 2),
    )

    @api.constrains('volume', 'administered_volume')
    def _check_volumes(self):
        self._check_non_negative([
            ('volume', 'حجم المحلول'),
            ('administered_volume', 'الحجم المعطى'),
        ])


class SaycareInpatientNursingFluidBalanceEntry(models.Model):
    _name = 'saycare.inpatient.nursing.fluid.balance.entry'
    _description = 'Inpatient Fluid Balance Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_datetime desc, id desc'
    _rec_name = 'entry_datetime'

    diagnosis = fields.Char(string='التشخيص (ICD-11)')
    entry_datetime = fields.Datetime(
        string='تاريخ ووقت التسجيل',
        required=True,
        index=True,
    )
    oral_intake = fields.Float(
        string='السوائل الداخلة بالفم',
        digits=(8, 2),
    )
    iv_intake = fields.Float(
        string='السوائل الداخلة بالوريد',
        digits=(8, 2),
    )
    total_intake = fields.Float(
        string='إجمالي السوائل الداخلة',
        compute='_compute_balance',
        store=True,
        digits=(8, 2),
    )
    urine_output = fields.Float(
        string='البول',
        digits=(8, 2),
    )
    drain_output = fields.Float(
        string='الدرنقة',
        digits=(8, 2),
    )
    total_output = fields.Float(
        string='إجمالي السوائل الخارجة',
        compute='_compute_balance',
        store=True,
        digits=(8, 2),
    )
    balance = fields.Float(
        string='توازن السوائل',
        compute='_compute_balance',
        store=True,
        digits=(8, 2),
    )

    @api.depends(
        'oral_intake',
        'iv_intake',
        'urine_output',
        'drain_output',
    )
    def _compute_balance(self):
        for record in self:
            record.total_intake = (
                record.oral_intake + record.iv_intake
            )
            record.total_output = (
                record.urine_output + record.drain_output
            )
            record.balance = (
                record.total_intake - record.total_output
            )

    @api.constrains(
        'oral_intake',
        'iv_intake',
        'urine_output',
        'drain_output',
    )
    def _check_amounts(self):
        self._check_non_negative([
            ('oral_intake', 'السوائل الداخلة بالفم'),
            ('iv_intake', 'السوائل الداخلة بالوريد'),
            ('urine_output', 'البول'),
            ('drain_output', 'الدرنقة'),
        ])


class SaycareInpatientNursingGlucoseEntry(models.Model):
    _name = 'saycare.inpatient.nursing.glucose.entry'
    _description = 'Inpatient Blood Glucose and Insulin Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'entry_date'

    diagnosis = fields.Char(string='التشخيص')
    entry_date = fields.Date(
        string='تاريخ قياس السكر',
        required=True,
        index=True,
    )
    entry_time = fields.Char(string='وقت قياس السكر')
    level = fields.Float(string='نسبة سكر الدم', digits=(8, 2))
    oral = fields.Boolean(string='بالفم', default=False)
    insulin_type = fields.Char(string='نوع الأنسولين')
    dose_units = fields.Float(string='الجرعة (وحدات)', digits=(8, 2))
    route = fields.Selection([
        ('sc', 'تحت الجلد'),
        ('iv', 'وريدي'),
        ('im', 'عضلي'),
        ('other', 'أخرى'),
    ], string='طريقة الإعطاء')
    site = fields.Selection([
        ('front_left_arm_23', 'الذراع الأيسر (أمامي) 23'),
        ('front_left_arm_24', 'الذراع الأيسر (أمامي) 24'),
        ('front_right_arm_21', 'الذراع الأيمن (أمامي) 21'),
        ('front_right_arm_26', 'الذراع الأيمن (أمامي) 26'),
        ('abdomen_left_13', 'يسار البطن 13'),
        ('abdomen_left_18', 'يسار البطن 18'),
        ('abdomen_center_20', 'وسط البطن 20'),
        ('abdomen_right_15', 'يمين البطن 15'),
        ('abdomen_right_17', 'يمين البطن 17'),
        ('front_left_thigh_25', 'الفخذ الأيسر (أمامي) 25'),
        ('front_left_thigh_13', 'الفخذ الأيسر (أمامي) 13'),
        ('front_left_thigh_1', 'الفخذ الأيسر (أمامي) 1'),
        ('front_right_thigh_26', 'الفخذ الأيمن (أمامي) 26'),
        ('front_right_thigh_14', 'الفخذ الأيمن (أمامي) 14'),
        ('front_right_thigh_2', 'الفخذ الأيمن (أمامي) 2'),
        ('back_left_arm_31', 'الذراع الأيسر (خلفي) 31'),
        ('back_left_arm_17', 'الذراع الأيسر (خلفي) 17'),
        ('back_right_arm_32', 'الذراع الأيمن (خلفي) 32'),
        ('back_right_arm_16', 'الذراع الأيمن (خلفي) 16'),
        ('back_left_flank_27', 'الخاصرة اليسرى (خلفي) 27'),
        ('back_left_flank_16', 'الخاصرة اليسرى (خلفي) 16'),
        ('back_right_flank_30', 'الخاصرة اليمنى (خلفي) 30'),
        ('back_right_flank_10', 'الخاصرة اليمنى (خلفي) 10'),
        ('back_left_hip_28', 'الأرداف اليسرى (خلفي) 28'),
        ('back_left_hip_12', 'الأرداف اليسرى (خلفي) 12'),
        ('back_left_hip_3', 'الأرداف اليسرى (خلفي) 3'),
        ('back_right_hip_29', 'الأرداف اليمنى (خلفي) 29'),
        ('back_right_hip_12', 'الأرداف اليمنى (خلفي) 12'),
        ('back_right_hip_9', 'الأرداف اليمنى (خلفي) 9'),
    ], string='مكان الحقن')
    urine_acetone = fields.Selection([
        ('negative', 'سلبي'),
        ('trace', 'أثر'),
        ('small', 'بسيط (+1)'),
        ('moderate', 'متوسط (+2)'),
        ('large', 'كبير (+3)'),
    ], string='الأسيتون في البول')
    notes = fields.Text(string='ملاحظات متابعة السكر')

    @api.constrains('level', 'dose_units')
    def _check_values(self):
        self._check_non_negative([
            ('level', 'نسبة سكر الدم'),
            ('dose_units', 'الجرعة'),
        ])


class SaycareInpatientNursingIcuLabEntry(models.Model):
    _name = 'saycare.inpatient.nursing.icu.lab.entry'
    _description = 'Inpatient ICU Lab Results Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'entry_date desc, id desc'
    _rec_name = 'entry_date'

    entry_date = fields.Date(
        string='تاريخ نتائج المعمل',
        required=True,
        index=True,
    )

    wbc = fields.Float(string='WBCs', digits=(10, 2))
    rbc = fields.Float(string='RBCs', digits=(10, 2))
    hb = fields.Float(string='Hb (gm%)', digits=(10, 2))
    hct = fields.Float(string='Hct (%)', digits=(10, 2))
    platelets = fields.Float(string='Platelets', digits=(10, 2))

    pt = fields.Float(string='PT', digits=(10, 2))
    pc = fields.Float(string='PC', digits=(10, 2))
    inr = fields.Float(string='INR', digits=(10, 2))
    ptt = fields.Float(string='PTT', digits=(10, 2))

    total_protein = fields.Float(string='Total Protein', digits=(10, 2))
    albumin = fields.Float(string='Albumin (mg%)', digits=(10, 2))
    t_bilirubin = fields.Float(string='T. Bilirubin', digits=(10, 2))
    d_bilirubin = fields.Float(string='D. Bilirubin', digits=(10, 2))
    alt_sgpt = fields.Float(string='ALT (SGPT)', digits=(10, 2))
    ast_sgot = fields.Float(string='AST (SGOT)', digits=(10, 2))
    alp = fields.Float(string='ALP', digits=(10, 2))

    urea = fields.Float(string='Urea', digits=(10, 2))
    creatinine = fields.Float(string='Creat (mg%)', digits=(10, 2))
    uric_acid = fields.Float(string='Uric Acid (mg)', digits=(10, 2))

    na = fields.Float(string='Na+ (meq/l)', digits=(10, 2))
    k = fields.Float(string='K+ (meq/l)', digits=(10, 2))
    ca = fields.Float(string='Ca++', digits=(10, 2))
    mg = fields.Float(string='Mg++', digits=(10, 2))
    po4 = fields.Float(string='PO4', digits=(10, 2))

    cpk = fields.Float(string='CPK', digits=(10, 2))
    cpk_mb = fields.Float(string='CPK-MB', digits=(10, 2))
    ldh = fields.Float(string='LDH', digits=(10, 2))
    troponin = fields.Float(string='Troponin', digits=(10, 2))

    cholesterol = fields.Float(string='Cholesterol', digits=(10, 2))
    triglycerides = fields.Float(string='Triglycerides', digits=(10, 2))
    ldl = fields.Float(string='LDL', digits=(10, 2))
    hdl = fields.Float(string='HDL', digits=(10, 2))

    ph = fields.Float(string='pH', digits=(6, 3))
    pco2 = fields.Float(string='PCO2', digits=(10, 2))
    o2_sat = fields.Float(string='O2 Sat', digits=(10, 2))
    hco3 = fields.Float(string='HCO3', digits=(10, 2))

    other_notes = fields.Text(string='نتائج معملية أخرى أو ملاحظات')

    @api.constrains('ph', 'o2_sat')
    def _check_ranges(self):
        for record in self:
            if record.ph and not 0 <= record.ph <= 14:
                raise ValidationError(
                    'قيمة pH يجب أن تكون من 0 إلى 14'
                )
            if record.o2_sat and not 0 <= record.o2_sat <= 100:
                raise ValidationError(
                    'تشبع الأكسجين يجب أن يكون من 0 إلى 100'
                )


class SaycareInpatientNursingPressureUlcerEntry(models.Model):
    _name = 'saycare.inpatient.nursing.pressure.ulcer.entry'
    _description = 'Inpatient Pressure Ulcer Follow-up Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'discovery_date desc, recorded_at desc, id desc'
    _rec_name = 'discovery_date'

    discovery_date = fields.Date(
        string='تاريخ اكتشاف القرحة',
        required=True,
        index=True,
    )
    location = fields.Selection([
        ('head', 'الرأس'),
        ('shoulder', 'الكتف'),
        ('sacrum', 'العجز (أسفل الظهر)'),
        ('buttock', 'الأرداف'),
        ('heel', 'الكعب'),
        ('other', 'أخرى'),
    ], string='مكان القرحة')
    grade = fields.Selection([
        ('stage1', 'المرحلة الأولى (احمرار الجلد)'),
        ('stage2', 'المرحلة الثانية (إصابة الجلد)'),
        ('stage3', 'المرحلة الثالثة (امتداد الإصابة للأنسجة)'),
        ('stage4', 'المرحلة الرابعة (وصول الإصابة للعظم)'),
    ], string='درجة القرحة')
    position = fields.Selection([
        ('front', 'الوضع الأمامي (على البطن)'),
        ('back', 'الوضع الخلفي (على الظهر)'),
        ('semi_sitting', 'نصف جالس'),
        ('right_side', 'النوم على الجانب الأيمن'),
        ('left_side', 'النوم على الجانب الأيسر'),
    ], string='وضعية نوم المريض')

    turning_chart_placed = fields.Boolean(
        string='وضع نموذج خريطة التقليب',
        default=False,
    )
    pressure_avoided = fields.Boolean(
        string='عدم الضغط على منطقة القرحة',
        default=False,
    )
    area_clean_dry = fields.Boolean(
        string='المحافظة على مكان القرحة نظيف وجاف',
        default=False,
    )
    air_mattress = fields.Boolean(
        string='وضع مرتبة هوائية',
        default=False,
    )
    wound_cleaned_saline = fields.Boolean(
        string='تنظيف الجرح بمحلول ملح وتجفيفه جيداً',
        default=False,
    )
    antibiotic_used = fields.Boolean(
        string='استعمال مضاد حيوي حسب أوامر الطبيب',
        default=False,
    )
    sterile_gauze_changed = fields.Boolean(
        string='وضع شاش معقم يتغير مرتين يومياً',
        default=False,
    )
    color_notes = fields.Char(string='لون القرحة')
    discharge_type = fields.Char(string='نوع الإفرازات')
    infection_signs_reported = fields.Boolean(
        string='تم إبلاغ الطبيب بعلامات العدوى',
        default=False,
    )
    care_plan = fields.Text(string='خطة الرعاية التمريضية')
    repositioning_education = fields.Boolean(
        string='تثقيف المريض أو الأهل لتجنب قرح الفراش',
        default=False,
    )


class SaycareInpatientNursingPhysicalRestraintEntry(models.Model):
    _name = 'saycare.inpatient.nursing.physical.restraint.entry'
    _description = 'Physician Physical Restraint Order & Nurse Follow-up Entry'
    _inherit = 'saycare.inpatient.nursing.sheet.entry.mixin'
    _order = 'follow_up_time desc, recorded_at desc, id desc'
    _rec_name = 'follow_up_time'

    department = fields.Char(string='القسم')
    admission_date = fields.Date(string='تاريخ الدخول')
    diagnosis = fields.Char(string='التشخيص')

    restraint_type = fields.Selection([
        ('chemical', 'كيميائي'),
        ('physical', 'جسدي'),
    ], string='نوع التقييد')
    chemical_given = fields.Selection([
        ('yes', 'نعم'),
        ('no', 'لا'),
    ], string='تم إعطاء علاج كيميائي')

    restraint_location_hand = fields.Selection([
        ('left', 'يسار'),
        ('right', 'يمين'),
        ('both', 'كلتاهما'),
    ], string='مكان التقييد - اليد')
    restraint_location_foot = fields.Selection([
        ('left', 'يسار'),
        ('right', 'يمين'),
        ('both', 'كلتاهما'),
    ], string='مكان التقييد - القدم')
    restraint_body = fields.Boolean(string='تقييد الجسم بالكامل (Body)')

    duration_type = fields.Selection([
        ('24h', '24 ساعة (الحد الأقصى)'),
        ('other', 'أخرى'),
    ], string='مدة التقييد')
    duration_other = fields.Char(string='تحديد المدة')
    release_frequency = fields.Char(string='عدد مرات فك التقييد')
    release_minutes = fields.Integer(string='مدة الفك (دقائق)')

    physician_evaluated = fields.Boolean(
        string='أقرّ الطبيب بتقييم المريض شخصياً وتحديد الحاجة للتقييد',
    )
    physician_sign = fields.Char(string='توقيع الطبيب')
    physician_time = fields.Char(string='وقت أمر الطبيب')
    physician_date = fields.Date(string='تاريخ أمر الطبيب')

    follow_up_time = fields.Char(string='وقت المتابعة', required=True)
    follow_up_notes = fields.Text(
        string='ملاحظة الممرضة أثناء التقييد (النبض - تورم - اللون)'
    )
    follow_up_sign = fields.Char(string='توقيع الممرضة')

    @api.constrains('release_minutes')
    def _check_release_minutes(self):
        self._check_non_negative([('release_minutes', 'مدة الفك')])
