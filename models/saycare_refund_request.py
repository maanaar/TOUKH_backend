# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareRefundRequest(models.Model):
    _name = 'saycare.refund.request'
    _description = 'Pending Refund Request (Doctor/Nurse -> Treasury)'
    _order = 'create_date desc'

    visit_id     = fields.Many2one('saycare.visit', string='الزيارة', ondelete='cascade', required=True)
    invoice_id   = fields.Many2one('account.move', string='الفاتورة')
    patient_id   = fields.Many2one('res.partner', string='المريض')
    patient_name = fields.Char(string='اسم المريض')
    amount       = fields.Float(string='المبلغ', digits=(12, 2))
    reason       = fields.Char(string='سبب الإلغاء')
    source       = fields.Selection([
        ('doctor', 'الطبيب'),
        ('nurse',  'التمريض'),
    ], string='المصدر')

    def _to_dict(self):
        return {
            'id':          self.id,
            'visitId':     self.visit_id.id,
            'invoiceId':   self.invoice_id.id if self.invoice_id else None,
            'patientName': self.patient_name or (self.patient_id.name if self.patient_id else ''),
            'amount':      self.amount or 0.0,
            'reason':      self.reason or '',
            'source':      self.source or '',
            'createdAt':   str(self.create_date) if self.create_date else '',
        }
