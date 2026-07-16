# -*- coding: utf-8 -*-
import json
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaycareGovExpenseAllocation(models.Model):
    _name = 'saycare.gov.expense.allocation'
    _description = 'Government Expense Monthly Allocation'
    _order = 'month_key asc'

    decision_id = fields.Many2one(
        'saycare.government.expense.decision',
        required=True, ondelete='cascade',
    )
    month_key = fields.Char(string='مفتاح الشهر')   # e.g. "2024-01"
    label      = fields.Char(string='الشهر')         # e.g. "يناير 2024"
    amount     = fields.Float(string='الحد الشهري',  digits=(12, 2))
    addition   = fields.Float(string='الإضافة',      digits=(12, 2))
    manual     = fields.Boolean(string='يدوي',        default=False)

    used_amount  = fields.Float(string='المستخدم',  digits=(12, 2), compute='_compute_usage', store=True)
    remaining    = fields.Float(string='المتبقي',   digits=(12, 2), compute='_compute_usage', store=True)
    state_label  = fields.Char(string='الحالة',     compute='_compute_usage', store=True)

    @api.depends('amount', 'decision_id.transaction_ids', 'decision_id.transaction_ids.parts_json')
    def _compute_usage(self):
        today_key = date.today().strftime('%Y-%m')
        for rec in self:
            used = 0.0
            for txn in rec.decision_id.transaction_ids:
                try:
                    for part in json.loads(txn.parts_json or '[]'):
                        if part.get('monthKey') == rec.month_key:
                            used += part.get('amount', 0)
                except Exception:
                    pass
            rec.used_amount = round(used, 2)
            rec.remaining   = round(max(0.0, rec.amount - used), 2)
            if rec.month_key:
                if rec.month_key < today_key:
                    rec.state_label = 'منتهي'
                elif rec.month_key == today_key:
                    rec.state_label = 'جاري'
                else:
                    rec.state_label = 'قادم'
            else:
                rec.state_label = ''


class SaycareGovExpenseClinic(models.Model):
    _name = 'saycare.gov.expense.clinic'
    _description = 'Government Expense Decision – Clinic Line'
    _order = 'id asc'

    decision_id = fields.Many2one(
        'saycare.government.expense.decision',
        ondelete='cascade', required=True,
    )
    specialty_id   = fields.Many2one('saycare.specialty', string='العيادة')
    specialty_name = fields.Char(string='اسم العيادة')

    # Services defined in saycare.service (source="service")
    service_ids = fields.Many2many(
        'saycare.service',
        'gov_expense_clinic_service_rel',
        'clinic_line_id', 'service_id',
        string='الخدمات (كتالوج)',
    )
    # Products used as services (source="product", e.g. lab/rad from product category)
    product_service_ids = fields.Many2many(
        'product.template',
        'gov_expense_clinic_product_svc_rel',
        'clinic_line_id', 'template_id',
        string='الخدمات (منتجات)',
    )
    # Medicines
    medicine_ids = fields.Many2many(
        'product.product',
        'gov_expense_clinic_medicine_rel',
        'clinic_line_id', 'product_id',
        string='الأدوية المسموحة',
    )

    def _to_dict(self):
        services = []
        for s in self.service_ids:
            services.append({
                'id': s.id,
                'code': s.code or '',
                'name': s.name or '',
                'category': 'عيادة',
                'price': s.price or 0,
                'insurance_price': s.insurance_price or 0,
                'source': 'service',
                'groupId': '',
                'groupLabel': '',
            })
        for t in self.product_service_ids:
            services.append({
                'id': t.id,
                'code': t.default_code or '',
                'name': t.name or '',
                'category': t.categ_id.name or '',
                'price': t.list_price or 0,
                'insurance_price': 0,
                'source': 'product',
                'groupId': '',
                'groupLabel': '',
            })
        medicines = []
        for p in self.medicine_ids:
            medicines.append({
                'productId': p.id,
                'variantId': p.id,
                'code': p.default_code or '',
                'name': p.name or '',
                'price': p.lst_price or 0,
                'uom': p.uom_id.name if p.uom_id else '',
                'category': p.categ_id.complete_name or '',
                'source': 'product',
                'groupId': str(p.categ_id.id) if p.categ_id else '',
                'groupLabel': p.categ_id.name or '',
            })
        return {
            'specialtyId': str(self.specialty_id.id) if self.specialty_id else '',
            'specialtyName': self.specialty_name or (self.specialty_id.name if self.specialty_id else ''),
            'allowedServices': services,
            'allowedMedicines': medicines,
            'serviceOptions': [],
        }


class SaycareGovernmentExpenseDecision(models.Model):
    _name = 'saycare.government.expense.decision'
    _description = 'Government Expense Decision'
    _order = 'id desc'

    name = fields.Char('اسم القرار', required=True)
    number = fields.Char('رقم القرار')
    start_date = fields.Date('تاريخ البداية')
    month_count = fields.Integer('عدد الأشهر', default=3)
    total_amount = fields.Float('إجمالي المبلغ', digits=(12, 2))
    status = fields.Selection([
        ('جاري', 'جاري'),
        ('منتهي', 'منتهي'),
        ('موقوف', 'موقوف'),
    ], string='الحالة', default='جاري', required=True)
    notes = fields.Text('ملاحظات')

    # اسم المستخدم الفعلي اللى أنشأ القرار من واجهة التطبيق — بيختلف عن
    # create_uid لأن كل طلبات الـ API بتتنفذ تحت نفس حساب أودو التقني.
    created_by_name = fields.Char('أنشأه', copy=False)

    # رقم صفحة واحد لكل مريض — كل قرارات نفس المريض، وكل الخدمات/المعاملات
    # المضافة عليها، بتشترك في نفس الرقم بدل ما كل قرار/خدمة ياخد رقم صفحة
    # مستقل (اللي كان بيسبب استهلاك أرقام الصفحات بسرعة من غير داعي). الفريدة
    # بقت على مستوى المريض مش على مستوى القرار نفسه (شوف _check_page_no).
    page_no = fields.Integer('رقم الصفحة', copy=False)

    def init(self):
        # كانت فريدة على مستوى القرار — دلوقتي ممكن كذا قرار لنفس المريض
        # يشتركوا في نفس الرقم قصداً، فمينفعش تفضل الفريدة دي على قاعدة
        # البيانات؛ الفحص بقى بايثوني (بيستثني قرارات نفس المريض) في
        # _check_page_no تحت.
        self.env.cr.execute("""
            DROP INDEX IF EXISTS saycare_gov_expense_decision_page_no_uniq
        """)

    @api.model
    def _sibling_page_no(self, patient_id):
        """Look up (without minting) a page number already assigned to
        another decision of the same patient. Returns 0 if none exists yet —
        callers that must NOT silently auto-mint (e.g. create() below, where
        a brand-new patient's number is typed by the finance user) rely on
        this distinction."""
        if patient_id:
            sibling = self.sudo().search([
                ('patient_id', '=', patient_id),
                ('page_no', '>', 0),
            ], limit=1)
            if sibling:
                return sibling.page_no
        return 0

    @api.model
    def _resolve_page_no_for_patient(self, patient_id):
        """Reuse an existing page number already assigned to another decision
        of the same patient; otherwise mint a fresh one. Only for self-healing
        paths (legacy decisions with no page_no yet, pharmacy transactions)
        where there is no form for a human to type a number into."""
        return self._sibling_page_no(patient_id) or self._next_page_no()

    @api.constrains('page_no', 'patient_id')
    def _check_page_no(self):
        for rec in self:
            if not rec.page_no:
                continue
            if rec.page_no <= 0:
                raise ValidationError('رقم الصفحة يجب أن يكون رقماً صحيحاً أكبر من صفر')
            conflict = self.sudo().search_count([
                ('page_no', '=', rec.page_no),
                ('id', '!=', rec.id),
                ('patient_id', '!=', rec.patient_id.id if rec.patient_id else False),
            ])
            if conflict:
                raise ValidationError('رقم الصفحة مستخدم بالفعل لمريض آخر')

    patient_id = fields.Many2one(
        'res.partner', string='المريض',
        domain=[('is_patient', '=', True)],
        ondelete='restrict',
    )

    clinic_ids = fields.One2many(
        'saycare.gov.expense.clinic', 'decision_id',
        string='العيادات المسموح بها',
    )

    # Kept for fallback on old decisions not yet re-saved through the UI
    allowed_clinics_json = fields.Text('العيادات (JSON قديم)', default='[]')
    allocations_json     = fields.Text('التوزيع الشهري', default='[]')
    allowed_groups_json  = fields.Text('المجموعات المسموح بها', default='{}')

    transaction_ids = fields.One2many(
        'saycare.government.expense.transaction', 'decision_id',
        string='المعاملات',
    )
    allocation_ids = fields.One2many(
        'saycare.gov.expense.allocation', 'decision_id',
        string='التوزيع الشهري',
    )

    # ── Editable per-decision deduction ──────────────────────────────────────
    deduction_amount = fields.Float(
        string='خصم المؤسسة', digits=(12, 2), default=60.0,
    )

    @api.model
    def _next_page_no(self):
        last = self.sudo().search([('page_no', '>', 0)], order='page_no desc', limit=1)
        return (last.page_no + 1) if last else 1

    @api.model_create_multi
    def create(self, vals_list):
        settings = self.env['saycare.government.expense.settings'].sudo().search([], limit=1)
        default_deduction = settings.deduction_amount if settings else 60.0
        for vals in vals_list:
            if 'deduction_amount' not in vals:
                vals['deduction_amount'] = default_deduction
            if not vals.get('page_no'):
                # لو المريض عنده قرار تاني بالفعل، ناخد رقمه تلقائي. لو ده أول
                # قرار للمريض ده، الرقم لازم يتكتب يدوي من شاشة المحاسبة —
                # مفيش رقم بيتولد لوحده هنا.
                vals['page_no'] = self._sibling_page_no(vals.get('patient_id'))
            if not vals.get('page_no'):
                raise ValidationError('رقم الصفحة مطلوب لأول قرار لهذا المريض')
        records = super().create(vals_list)
        # لو المريض عنده قرارات تانية لسه من غير رقم صفحة (اتسجلت قبل الميزة
        # دي)، نديهم نفس رقم القرار الجديد عشان كل قرارات نفس المريض تتساوى.
        for rec in records:
            if rec.patient_id and rec.page_no:
                siblings = self.sudo().search([
                    ('patient_id', '=', rec.patient_id.id),
                    ('id', '!=', rec.id),
                    ('page_no', '=', 0),
                ])
                if siblings:
                    siblings.write({'page_no': rec.page_no})
        return records

    # ── Computed summary (reads deduction_amount from the record itself) ──────
    distributable_amount = fields.Float(string='الصافي للتوزيع',  digits=(12, 2), compute='_compute_summary')
    allocated_total      = fields.Float(string='الموزع',          digits=(12, 2), compute='_compute_summary')
    used_total           = fields.Float(string='إجمالي المستخدم', digits=(12, 2), compute='_compute_summary')
    usable_remaining     = fields.Float(string='المتاح',          digits=(12, 2), compute='_compute_summary')
    expired_amount       = fields.Float(string='منتهي',           digits=(12, 2), compute='_compute_summary')

    @api.depends('total_amount', 'deduction_amount', 'allocation_ids.amount',
                 'allocation_ids.used_amount', 'allocation_ids.month_key', 'transaction_ids.amount')
    def _compute_summary(self):
        today_key = date.today().strftime('%Y-%m')
        for rec in self:
            rec.distributable_amount = round(max(0.0, rec.total_amount - rec.deduction_amount), 2)
            rec.allocated_total      = round(sum(a.amount for a in rec.allocation_ids), 2)
            rec.used_total           = round(sum(t.amount for t in rec.transaction_ids), 2)
            usable  = sum(a.remaining for a in rec.allocation_ids if (a.month_key or '') >= today_key)
            expired = sum(a.remaining for a in rec.allocation_ids if (a.month_key or '') <  today_key)
            rec.usable_remaining = round(usable,  2)
            rec.expired_amount   = round(expired, 2)

    scans_ids = fields.Many2many(
        'product.template',
        'gov_expense_decision_scans_product_rel', 'decision_id', 'product_id',
        string='الأشعة المسموح بها',
    )
    test_ids = fields.Many2many(
        'product.template',
        'gov_expense_decision_tests_product_rel', 'decision_id', 'product_id',
        string='التحاليل المسموح بها',
    )
    specialty_ids = fields.Many2many(
        'saycare.specialty',
        'gov_expense_decision_specialty_rel', 'decision_id', 'specialty_id',
        string='العيادات المسموح بها',
    )
    medicine_categ_ids = fields.Many2many(
        'product.category',
        'gov_expense_decision_medicine_categ_rel', 'decision_id', 'categ_id',
        string='مجموعات الأدوية المسموح بها',
        domain="[('parent_id.name', 'ilike', 'medications')]",
    )

    def _to_dict(self):
        # Build allowedClinics from specialty_ids (simple M2M), fall back to legacy
        if self.specialty_ids:
            allowed_clinics = [
                {
                    'specialtyId': str(s.id),
                    'specialtyName': s.name_ar if hasattr(s, 'name_ar') and s.name_ar else s.name,
                    'allowedServices': [],
                    'allowedMedicines': [],
                }
                for s in self.specialty_ids
            ]
        elif self.clinic_ids:
            allowed_clinics = [c._to_dict() for c in self.clinic_ids]
        else:
            allowed_clinics = self._load_json('allowed_clinics_json', [])

        # Build allowedGroups from M2M fields, fall back to JSON if empty
        medicines = [{'id': str(c.id), 'label': c.name_ar if hasattr(c, 'name_ar') and c.name_ar else c.name} for c in self.medicine_categ_ids]
        labs      = [{'id': str(t.id), 'label': t.name} for t in self.test_ids]
        radiology = [{'id': str(s.id), 'label': s.name} for s in self.scans_ids]
        if not medicines and not labs and not radiology:
            allowed_groups = self._load_json('allowed_groups_json', {'medicines': [], 'labs': [], 'radiology': []})
        else:
            allowed_groups = {'medicines': medicines, 'labs': labs, 'radiology': radiology}

        return {
            'id': self.id,
            'name': self.name or '',
            'number': self.number or '',
            'startDate': str(self.start_date) if self.start_date else '',
            'monthCount': self.month_count or 3,
            'totalAmount': self.total_amount or 0.0,
            'deductionAmount': self.deduction_amount or 0.0,
            'status': self.status or 'جاري',
            'notes': self.notes or '',
            'createdByName': self.created_by_name or self.create_uid.name or '',
            'pageNo': self.page_no if self.page_no > 0 else None,
            'patient': {
                'id': self.patient_id.id if self.patient_id else None,
                'name': self.patient_id.name or '' if self.patient_id else '',
                'mrn': self.patient_id.mrn or '' if self.patient_id else '',
                'nationalId': self.patient_id.id_number or '' if self.patient_id else '',
                'mobile': self.patient_id.phone or '' if self.patient_id else '',
            },
            'allowedClinics': allowed_clinics,
            'allocations': [
                {
                    'monthKey': a.month_key,
                    'label':    a.label,
                    'amount':   a.amount,
                    'addition': a.addition,
                    'manual':   a.manual,
                }
                for a in self.allocation_ids.sorted('month_key')
            ] if self.allocation_ids else self._load_json('allocations_json', []),
            'allowedGroups':  allowed_groups,
            'transactions': [t._to_dict() for t in self.transaction_ids.sorted('id')],
            'scans': [{'id': s.id, 'name': s.name} for s in self.scans_ids],
            'tests': [{'id': t.id, 'name': t.name} for t in self.test_ids],
        }

    def _to_list_dict(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'number': self.number or '',
            'startDate': str(self.start_date) if self.start_date else '',
            'totalAmount': self.total_amount or 0.0,
            'usableRemaining': self.usable_remaining or 0.0,
            'status': self.status or 'جاري',
            'createdByName': self.created_by_name or self.create_uid.name or '',
            'pageNo': self.page_no if self.page_no > 0 else None,
            'patient': {
                'id': self.patient_id.id if self.patient_id else None,
                'name': self.patient_id.name or '' if self.patient_id else '',
                'mrn': self.patient_id.mrn or '' if self.patient_id else '',
                'nationalId': self.patient_id.id_number or '' if self.patient_id else '',
                'mobile': self.patient_id.phone or '' if self.patient_id else '',
            },
        }

    def _load_json(self, field_name, default):
        raw = getattr(self, field_name, None)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default


class SaycareGovernmentExpenseSettings(models.Model):
    _name = 'saycare.government.expense.settings'
    _description = 'Government Expense Decision Settings'

    name = fields.Char(default='إعدادات قرارات نفقة الدولة', readonly=True)
    deduction_amount = fields.Float('المبلغ المخصوم', default=60.0, digits=(12, 2))
    max_addition_amount = fields.Float('أقصى مبلغ إضافة للشهر', default=40.0, digits=(12, 2))

    @api.model
    def get_settings(self):
        rec = self.sudo().search([], limit=1)
        if not rec:
            rec = self.sudo().create({})
        return rec

    def action_open_settings(self):
        """Always open the one persisted settings record, never a blank/new one."""
        settings = self.get_settings()
        return {
            'type':     'ir.actions.act_window',
            'name':     'إعدادات القرارات',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id':   settings.id,
            'target':   'current',
        }

    def _to_dict(self):
        return {
            'deductionAmount': self.deduction_amount or 0.0,
            'maxAdditionAmount': self.max_addition_amount or 0.0,
        }


class SaycareGovernmentExpenseTransaction(models.Model):
    _name = 'saycare.government.expense.transaction'
    _description = 'Government Expense Transaction'
    _order = 'date desc, id desc'

    decision_id = fields.Many2one(
        'saycare.government.expense.decision',
        string='القرار', required=True, ondelete='cascade',
    )
    # Kept only for historical records created before رقم الصفحة was introduced.
    reference_no = fields.Char('رقم المرجع القديم')
    page_no = fields.Integer('رقم الصفحة', copy=False, index=True)
    date = fields.Date('التاريخ')
    item_type = fields.Selection(
        [('service', 'خدمة'), ('medicine', 'دواء')],
        string='النوع', default='service',
    )
    specialty_id = fields.Char('معرف التخصص')
    specialty_name = fields.Char('اسم التخصص')
    item_id = fields.Char('معرف البند')
    item_name = fields.Char('اسم البند')
    category = fields.Char('الفئة')
    amount = fields.Float('المبلغ', digits=(12, 2))
    qty = fields.Integer('الكمية', default=1)
    parts_json = fields.Text('التوزيع الشهري', default='[]')
    touches_future_month = fields.Boolean('يمس شهر مستقبلي', default=False)
    notes = fields.Text('ملاحظات')

    deducted = fields.Float(string='المخصوم فعلياً', digits=(12, 2), compute='_compute_deducted', store=True)

    def init(self):
        # رقم الصفحة بقى بيتشارك بين كل معاملات نفس القرار (شايف page_no على
        # الـ decision نفسه) — الفريدة اتنقلت هناك، فمينفعش تفضل هنا فريدة
        # على مستوى الترانزاكشن لأن كذا معاملة هيبقى ليهم نفس الرقم قصداً.
        self.env.cr.execute("""
            DROP INDEX IF EXISTS saycare_gov_expense_transaction_page_no_uniq
        """)

    @api.depends('parts_json')
    def _compute_deducted(self):
        for rec in self:
            try:
                parts = json.loads(rec.parts_json or '[]')
                rec.deducted = round(sum(p.get('amount', 0) for p in parts), 2)
            except Exception:
                rec.deducted = 0.0

    def _to_dict(self):
        parts = []
        if self.parts_json:
            try:
                parts = json.loads(self.parts_json)
            except Exception:
                pass
        page_no = self.decision_id.page_no if self.decision_id and self.decision_id.page_no else self.page_no
        return {
            'id': self.id,
            'pageNo': page_no if page_no and page_no > 0 else None,
            'referenceNo': self.reference_no or '',
            'date': str(self.date) if self.date else '',
            'itemType': self.item_type or 'service',
            'specialtyId': self.specialty_id or '',
            'specialtyName': self.specialty_name or '',
            'itemId': self.item_id or '',
            'itemName': self.item_name or '',
            'category': self.category or '',
            'amount': self.amount or 0.0,
            'qty': self.qty or 1,
            'parts': parts,
            'touchesFutureMonth': self.touches_future_month or False,
            'notes': self.notes or '',
        }
