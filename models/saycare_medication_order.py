# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareMedicationOrder(models.Model):
    _name        = 'saycare.medication.order'
    _description = 'Medication Order / Prescription'
    _order       = 'prescribed_at desc, id desc'

    # ── Links ─────────────────────────────────────────────────────────────────
    visit_id   = fields.Many2one('saycare.visit',   string='Visit',   ondelete='cascade', index=True)
    patient_id = fields.Many2one('res.partner',      string='Patient', ondelete='restrict', index=True)

    # ── Drug ──────────────────────────────────────────────────────────────────
    product_id = fields.Many2one('product.product', string='Drug (Product)')
    drug_name  = fields.Char(string='Drug Name')

    # ── Dosing ────────────────────────────────────────────────────────────────
    dose        = fields.Char(string='Dose')
    frequency   = fields.Char(string='Frequency')
    duration    = fields.Char(string='Duration')

    route = fields.Selection([
        ('oral',        'فموي'),
        ('iv',          'وريدي IV'),
        ('im',          'عضلي IM'),
        ('sc',          'تحت الجلد SC'),
        ('topical',     'موضعي'),
        ('inhalation',  'استنشاق'),
        ('rectal',      'شرجي'),
        ('sublingual',  'تحت اللسان'),
    ], string='Route', default='oral')

    instructions = fields.Text(string='Instructions')

    # ── Quantity ──────────────────────────────────────────────────────────────
    quantity = fields.Float(string='Quantity', default=1.0)
    uom_id   = fields.Many2one('uom.uom', string='Unit')

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('active',     'نشط'),
        ('dispensed',  'صُرِف'),
        ('cancelled',  'ملغي'),
        ('on_hold',    'موقوف'),
    ], string='Status', default='active', index=True)

    cancel_reason = fields.Char(string='Cancel Reason')

    # ── Prescribed ────────────────────────────────────────────────────────────
    prescribed_by = fields.Many2one('hr.employee', string='Prescribed By')
    prescribed_at = fields.Datetime(string='Prescribed At', default=fields.Datetime.now)

    # ── Dispensed ─────────────────────────────────────────────────────────────
    dispensed_by = fields.Many2one('hr.employee', string='Dispensed By')
    dispensed_at = fields.Datetime(string='Dispensed At')
