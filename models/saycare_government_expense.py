# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class SaycareGovernmentExpenseDecision(models.Model):
    _name = 'saycare.government.expense.decision'
    _description = 'Government Expense Decision'
    _order = 'id desc'

    name = fields.Char('اسم القرار', required=True)
    number = fields.Char('رقم القرار', required=True)
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

    # JSON blobs to avoid extra tables for complex nested structures
    allowed_clinics_json = fields.Text('العيادات المسموح بها', default='[]')
    allocations_json = fields.Text('التوزيع الشهري', default='[]')

    transaction_ids = fields.One2many(
        'saycare.government.expense.transaction', 'decision_id',
        string='المعاملات',
    )

    def _to_dict(self):
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
            'allowedClinics': self._load_json('allowed_clinics_json', []),
            'allocations': self._load_json('allocations_json', []),
            'transactions': [t._to_dict() for t in self.transaction_ids.sorted('id')],
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
