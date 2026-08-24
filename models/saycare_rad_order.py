# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareRadOrder(models.Model):
    _name        = 'saycare.rad.order'
    _description = 'Radiology Order'
    _order       = 'requested_at desc'

    visit_id            = fields.Many2one('saycare.visit',  ondelete='cascade',  index=True)
    patient_id          = fields.Many2one('res.partner',    ondelete='restrict', index=True,
                                          domain=[('is_patient', '=', True)])
    service_id          = fields.Many2one('saycare.service', string='Service',
                                          ondelete='set null', index=True)
    # أشعة catalog items are searched via categ_keyword against product
    # categories, not saycare.service records (see services.py get_all —
    # categ_keyword-only calls skip saycare.service entirely) — so a rad
    # order created from that search must link a product, not a service.
    product_id          = fields.Many2one('product.template', string='Product',
                                          ondelete='set null', index=True)
    request_group       = fields.Char(string='Request Group', index=True, copy=False)
    study_type          = fields.Char(string='Study Type', required=True)
    body_part           = fields.Char(string='Body Part')
    clinical_indication = fields.Text(string='Clinical Indication')
    notes               = fields.Text(string='Notes')
    state               = fields.Selection([
        ('requested',  'مطلوب'),
        ('scheduled',  'مجدول'),
        ('done',       'منجز'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='requested', index=True)
    result_notes        = fields.Text(string='Result Notes')
    result_at           = fields.Datetime(string='Result At')
    requested_by        = fields.Many2one('hr.employee', string='Requested By')
    requested_at        = fields.Datetime(string='Requested At', default=fields.Datetime.now)

    # ── Nursing worklist status (distinct from rad `state` above) ─────────────
    nurse_status = fields.Selection([
        ('pending',   'معلق'),
        ('accepted',  'تم القبول'),
        ('completed', 'مكتمل'),
        ('held',      'معلّق (متوقف)'),
    ], string='حالة التمريض', default='pending', index=True)
    nurse_status_by = fields.Many2one('hr.employee', string='قام بالإجراء (تمريض)')
    nurse_status_at = fields.Datetime(string='وقت آخر تحديث تمريضي')
