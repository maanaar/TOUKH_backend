# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareVisit(models.Model):
    _name        = 'saycare.visit'
    _description = 'Patient Visit'
    _order       = 'admission_date desc, id desc'
    _rec_name    = 'name'

    name           = fields.Char(string='Visit Reference', required=True, copy=False,
                                 readonly=True, default='New')
    patient_id     = fields.Many2one('res.partner', string='Patient',
                                     domain=[('is_patient', '=', True)],
                                     ondelete='restrict', index=True, required=True)
    admission_date = fields.Datetime(string='Admission Date', default=fields.Datetime.now, index=True)
    discharge_date = fields.Datetime(string='Discharge Date')

    state = fields.Selection([
        ('pending_payment', 'بانتظار السداد'),
        ('diagnostic',      'خدمة تشخيصية'),
        ('waiting',         'في الانتظار'),
        ('triage',       'قيد التقييم'),
        ('doctor_queue', 'انتظار الطبيب'),
        ('in_progress',  'قيد الفحص'),
        ('done',         'مكتمل'),
        ('cancelled',    'ملغي'),
    ], string='Status', default='waiting', index=True)

    visit_type = fields.Selection([
        ('outpatient',   'كشف'),
        ('inpatient',    'داخلي'),
        ('emergency',    'طوارئ'),
        ('consultation', 'استشارة'),
    ], string='نوع الزيارة', default='outpatient')

    request_source = fields.Selection([
        ('reception',         'الاستقبال'),
        ('doctor',            'الطبيب'),
        ('lab',               'المعمل'),
        ('external_services', 'الخدمات الخارجية'),
    ], string='مصدر الطلب', default='reception', index=True)

    diagnostic_type = fields.Selection([
        ('lab', 'تحاليل'),
        ('rad', 'أشعة'),
    ], string='نوع الخدمة التشخيصية', index=True)

    specialty_id = fields.Many2one('saycare.specialty', string='Specialty')
    doctor_id    = fields.Many2one('hr.employee', string='Doctor',
                                   domain=[('medical_role', '=', 'doctor')])
    nurse_id     = fields.Many2one('hr.employee', string='Nurse',
                                   domain=[('medical_role', '=', 'nurse')])

    financial_class = fields.Selection([
        ('cash',         'نقدي'),
        ('state',        'نفقة الدولة'),
        ('consultation', 'مشورة'),
        ('takaful',      'تكافل وكرامة'),
        ('insurance',    'تأمين صحى'),
        ('contract',     'تعاقدات'),
        ('moh',          'وزارة الصحة'),
        ('staff',        'عاملين'),
    ], string='الوجهة المالية')

    payment_method = fields.Selection([
        ('cash',     'نقدي'),
        ('deferred', 'فيزا'),
    ], string='طريقة الدفع', default='cash')

    chief_complaint = fields.Char(string='Chief Complaint')
    triage_notes    = fields.Text(string='Triage Notes')

    # ── Emergency reception fields ─────────────────────────────────────────────
    arrival_mode = fields.Selection([
        ('walk_in',   'مشياً'),
        ('ambulance', 'إسعاف'),
        ('police',    'شرطة'),
        ('referral',  'تحويل'),
    ], string='طريقة الوصول')
    companion_name = fields.Char(string='اسم المرافق')
    # حالة المريض عند الاستقبال - يظهر حقول إضافية حسب الاختيار: حوادث تحتاج
    # بيانات المسعف/السيارة، وحالات رعايات مصر تحتاج جهة التحويل من/إلى.
    case_status = fields.Selection([
        ('death_outside',   'وفاة من الخارج'),
        ('death_reception', 'وفاة بالاستقبال'),
        ('accident',        'حوادث'),
        ('egypt_referral',  'حالات رعايات مصر'),
    ], string='حالة المريض')
    accident_rescuer_name   = fields.Char(string='اسم المسعف')
    accident_car_number     = fields.Char(string='رقم السيارة')
    accident_location       = fields.Char(string='مكان الحادث')
    accident_rescuer_phone  = fields.Char(string='رقم المسعف')
    referral_from           = fields.Char(string='محول من')
    referral_to             = fields.Char(string='محول إلي')
    exit_status = fields.Selection([
        ('home',              'خروج للمنزل'),
        ('critical_care',     'حجز بالرعاية'),
        ('inpatient',         'حجز بالداخلي'),
        ('operations',        'عمليات'),
        ('against_advice',    'خروج الحالة على المسؤولية'),
        ('absconded',         'هروب الحالة'),
        ('not_reached_3_shifts', 'عدم الوصول للحالة على مدار ثلاث شيفتات'),
    ], string='حالة خروج المريض')

    # ── Kiosk self-service queue tickets ───────────────────────────────────────
    reception_number = fields.Char(string='رقم انتظار الاستقبال')
    queue_number      = fields.Char(string='رقم انتظار العيادة')

    # ── Triage assessment fields ────────────────────────────────────────────────
    consciousness_level = fields.Selection([
        ('alert',        'واعي ومتنبه'),
        ('voice',        'يستجيب للصوت'),
        ('pain',         'يستجيب للألم'),
        ('unresponsive', 'غير مستجيب'),
    ], string='درجة الوعي')
    skin_color = fields.Selection([
        ('normal',     'طبيعي'),
        ('pale',       'شاحب'),
        ('cyanotic',   'مزرق'),
        ('flushed',    'محمر'),
        ('jaundiced',  'مصفر'),
    ], string='لون الجلد')
    allergy_status = fields.Selection([
        ('none',    'لا توجد حساسية معروفة'),
        ('present', 'توجد حساسية'),
        ('unknown', 'غير معروف'),
    ], string='الحساسية')
    neuro_response = fields.Selection([
        ('normal',       'طبيعية'),
        ('voice',        'يستجيب للصوت'),
        ('pain',         'يستجيب للألم'),
        ('unresponsive', 'غير مستجيب'),
    ], string='الاستجابة العصبية')
    pain_scale = fields.Integer(string='مقياس الألم')
    triage_color = fields.Selection([
        ('red',    'أحمر'),
        ('yellow', 'أصفر'),
        ('green',  'أخضر'),
        ('blue',   'أزرق'),
        ('white',  'أبيض'),
    ], string='تصنيف الفرز')

    room_id = fields.Many2one('hospital.room', string='الغرفة')
    bed_id  = fields.Many2one('hospital.bed', string='السرير')

    medication_order_ids = fields.One2many('saycare.medication.order', 'visit_id',
                                           string='Medication Orders')
    vital_sign_ids       = fields.One2many('saycare.vital.signs',    'visit_id',
                                           string='Vital Signs')
    clinical_note_ids    = fields.One2many('saycare.clinical.note',  'visit_id',
                                           string='Clinical Notes')
    lab_order_ids        = fields.One2many('saycare.lab.order',      'visit_id',
                                           string='Lab Orders')
    rad_order_ids        = fields.One2many('saycare.rad.order',      'visit_id',
                                           string='Rad Orders')

    notes       = fields.Text(string='Notes')
    basket_json = fields.Text(string='Basket JSON', default='[]')
    basket_paid = fields.Boolean(string='Basket Paid', default=False)

    # ── Financial detail fields ────────────────────────────────────────────────
    decision_no        = fields.Char(string='رقم القرار')
    expiry_date        = fields.Date(string='تاريخ الانتهاء')
    available_balance  = fields.Float(string='الرصيد المتاح')
    covered_services   = fields.Char(string='الخدمات المغطاة')
    contract_entity    = fields.Char(string='جهة التعاقد')
    co_pay_percent     = fields.Char(string='نسبة التحمل')
    approval_required  = fields.Boolean(string='يتطلب موافقة', default=False)
    admin_letter_no    = fields.Char(string='رقم الخطاب الإداري')
    issuing_authority  = fields.Char(string='جهة الإصدار')
    card_number        = fields.Char(string='رقم الكارت')
    receipt_no         = fields.Char(string='رقم الايصال')
    financial_notes    = fields.Text(string='ملاحظات مالية')
    employee_id_no     = fields.Char(string='الرقم الوظيفي')
    department         = fields.Char(string='الإدارة / القسم')

    # اسم المستخدم الفعلي اللى سجل الزيارة من واجهة التطبيق — بيختلف عن
    # create_uid لأن كل طلبات الـ API بتتنفذ تحت نفس حساب أودو التقني.
    created_by_name = fields.Char('أنشأه', copy=False)

    invoice_id  = fields.Many2one('account.move', string='Invoice', ondelete='set null')

    service_ids = fields.Many2many(
        'saycare.service', 'saycare_visit_service_rel',
        'visit_id', 'service_id',
        string='Services',
    )

    total_price     = fields.Float(string='Total Price',     compute='_compute_totals', store=True)
    insurance_share = fields.Float(string='Insurance Share', compute='_compute_totals', store=True)
    patient_share   = fields.Float(string='Patient Share',   compute='_compute_totals', store=True)

    @api.depends('service_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_price     = sum(rec.service_ids.mapped('price'))
            rec.insurance_share = sum(rec.service_ids.mapped('insurance_price'))
            rec.patient_share   = max(0.0, rec.total_price - rec.insurance_share)

    def create(self, vals_list):
        for vals in (vals_list if isinstance(vals_list, list) else [vals_list]):
            if vals.get('name', 'New') == 'New':
                seq_code = 'saycare.visit'
                if vals.get('visit_type') == 'emergency':
                    patient = self.env['res.partner'].browse(vals['patient_id']) if vals.get('patient_id') else None
                    is_unknown = bool(patient and patient.patient_type == 'unknown')
                    seq_code = 'saycare.visit.emergency.unknown' if is_unknown else 'saycare.visit.emergency'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
        return super().create(vals_list)
