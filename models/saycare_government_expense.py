# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


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

    scans_ids = fields.Many2many(
        'product.category',
        'gov_expense_decision_scans_rel', 'decision_id', 'categ_id',
        string='اشاعات',
    )
    test_ids = fields.Many2many(
        'product.category',
        'gov_expense_decision_tests_rel', 'decision_id', 'categ_id',
        string='التحاليل',
    )

    def _to_dict(self):
        if self.clinic_ids:
            allowed_clinics = [c._to_dict() for c in self.clinic_ids]
        else:
            allowed_clinics = self._load_json('allowed_clinics_json', [])
        return {
            'id': self.id,
            'name': self.name or '',
            'number': self.number or '',
            'startDate': str(self.start_date) if self.start_date else '',
            'monthCount': self.month_count or 3,
            'totalAmount': self.total_amount or 0.0,
            'status': self.status or 'جاري',
            'notes': self.notes or '',
            'patient': {
                'id': self.patient_id.id if self.patient_id else None,
                'name': self.patient_id.name or '' if self.patient_id else '',
                'mrn': self.patient_id.mrn or '' if self.patient_id else '',
                'nationalId': self.patient_id.id_number or '' if self.patient_id else '',
                'mobile': self.patient_id.phone or '' if self.patient_id else '',
            },
            'allowedClinics': allowed_clinics,
            'allocations':    self._load_json('allocations_json', []),
            'allowedGroups':  self._load_json('allowed_groups_json', {'medicines': [], 'labs': [], 'radiology': []}),
            'transactions': [t._to_dict() for t in self.transaction_ids.sorted('id')],
            'scans': [{'id': c.id, 'name': c.name} for c in self.scans_ids],
            'tests': [{'id': c.id, 'name': c.name} for c in self.test_ids],
        }

    def _load_json(self, field_name, default):
        raw = getattr(self, field_name, None)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default


class SaycareGovernmentExpenseTransaction(models.Model):
    _name = 'saycare.government.expense.transaction'
    _description = 'Government Expense Transaction'
    _order = 'date desc, id desc'

    decision_id = fields.Many2one(
        'saycare.government.expense.decision',
        string='القرار', required=True, ondelete='cascade',
    )
    reference_no = fields.Char('رقم المرجع')
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

    def _to_dict(self):
        parts = []
        if self.parts_json:
            try:
                parts = json.loads(self.parts_json)
            except Exception:
                pass
        return {
            'id': self.id,
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
