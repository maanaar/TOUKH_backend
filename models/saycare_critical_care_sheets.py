# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaycareCriticalCareSheetEntryMixin(models.AbstractModel):
    _name = 'saycare.critical.care.sheet.entry.mixin'
    _description = 'Critical Care Sheet Entry Mixin'

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


class SaycareCriticalCareVitalEntry(models.Model):
    _name = 'saycare.critical.care.vital.entry'
    _description = 'Critical Care Vital Signs Entry'
    _inherit = 'saycare.critical.care.sheet.entry.mixin'
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


class SaycareCriticalCareNursingPlanEntry(models.Model):
    _name = 'saycare.critical.care.nursing.plan.entry'
    _description = 'Critical Care Nursing Care Plan Entry'
    _inherit = 'saycare.critical.care.sheet.entry.mixin'
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


class SaycareCriticalCareTreatmentEntry(models.Model):
    _name = 'saycare.critical.care.treatment.entry'
    _description = 'Critical Care Treatment Description Entry'
    _inherit = 'saycare.critical.care.sheet.entry.mixin'
    _order = 'entry_date desc, entry_time desc, id desc'
    _rec_name = 'medication_name'

    doctor_name = fields.Char(string='الطبيب المعالج')
    diagnosis = fields.Char(string='التشخيص')
    entry_date = fields.Date(string='تاريخ وصف العلاج', index=True)
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


class SaycareCriticalCareIvInfusionEntry(models.Model):
    _name = 'saycare.critical.care.iv.infusion.entry'
    _description = 'Critical Care IV Infusion Entry'
    _inherit = 'saycare.critical.care.sheet.entry.mixin'
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


class SaycareCriticalCareIcuLabEntry(models.Model):
    _name = 'saycare.critical.care.icu.lab.entry'
    _description = 'Critical Care ICU Lab Results Entry'
    _inherit = 'saycare.critical.care.sheet.entry.mixin'
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
