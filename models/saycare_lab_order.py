# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareLabOrder(models.Model):

    _name        = 'saycare.lab.order'
    _description = 'Laboratory Order'
    _order       = 'requested_at desc'

    visit_id     = fields.Many2one('saycare.visit',  ondelete='cascade',  index=True)
    patient_id   = fields.Many2one('res.partner',    ondelete='restrict', index=True,
                                   domain=[('is_patient', '=', True)])
    service_id   = fields.Many2one('saycare.service', string='Service',
                                   ondelete='set null', index=True)
    # The لab test catalog (/saycare/api/lab-tests) is sourced straight from
    # product.template, a different id space than saycare.service — most lab
    # tests only ever resolve here, never to service_id. Mirrors
    # saycare.rad.order.product_id.
    product_id   = fields.Many2one('product.template', string='Product',
                                   ondelete='set null', index=True)
    request_group = fields.Char(string='Request Group', index=True, copy=False)
    test_name    = fields.Char(string='Test Name', required=True)
    test_code    = fields.Char(string='Test Code')
    priority     = fields.Selection([
        ('routine', 'روتيني'),
        ('urgent',  'عاجل'),
        ('stat',    'فوري'),
    ], string='Priority', default='routine')
    notes        = fields.Text(string='Notes')
    state        = fields.Selection([
        ('requested',  'مطلوب'),
        ('collected',  'تم التحصيل'),
        ('resulted',   'النتائج جاهزة'),
        ('cancelled',  'ملغي'),
    ], string='Status', default='requested', index=True)
    result_value  = fields.Text(string='Result')
    result_at     = fields.Datetime(string='Result At')
    requested_by  = fields.Many2one('hr.employee', string='Requested By')
    requested_at  = fields.Datetime(string='Requested At', default=fields.Datetime.now)

    # ── Nursing worklist status (distinct from lab `state` above) ─────────────
    # Mirrors saycare.rad.order/saycare.medication.order — nursing_worklist.py's
    # _task_from_lab already expected this field to exist; it just never got
    # added here, which only surfaced once a lab order could actually be
    # created for an inpatient visit.
    nurse_status = fields.Selection([
        ('pending',   'معلق'),
        ('accepted',  'تم القبول'),
        ('completed', 'مكتمل'),
        ('held',      'معلّق (متوقف)'),
    ], string='حالة التمريض', default='pending', index=True)
    nurse_status_by = fields.Many2one('hr.employee', string='قام بالإجراء (تمريض)')
    nurse_status_at = fields.Datetime(string='وقت آخر تحديث تمريضي')
