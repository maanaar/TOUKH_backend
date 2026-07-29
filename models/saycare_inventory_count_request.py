# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycareInventoryCountRequest(models.Model):
    """طلب جرد لمخزن واحد — يمر بمرحلة اعتماد واحدة من لجنة الجرد قبل أن
    يُرحَّل تلقائياً كتسوية جرد فعلية على stock.quant."""
    _name        = 'saycare.inventory.count.request'
    _description = 'Inventory Count Request'
    _order       = 'create_date desc'
    _rec_name    = 'name'

    name = fields.Char(string='رقم الطلب', copy=False, readonly=True, default='مسودة جديدة')

    warehouse_id = fields.Many2one('stock.warehouse', string='المخزن', required=True, ondelete='restrict')
    user_id      = fields.Many2one('res.users', string='مسؤول الجرد', default=lambda self: self.env.uid)
    date         = fields.Date(string='تاريخ الجرد', default=fields.Date.context_today)
    notes        = fields.Text(string='ملاحظات عامة')

    state = fields.Selection([
        ('draft',    'مسودة'),
        ('review',   'بانتظار اعتماد اللجنة'),
        ('approved', 'معتمد'),
        ('posted',   'تم الترحيل للجرد الفعلي'),
        ('rejected', 'مرفوض للتعديل'),
    ], string='الحالة', default='draft', index=True, copy=False)

    member_user_id      = fields.Many2one('res.users', string='اعتمده', copy=False, readonly=True)
    member_approved_at  = fields.Datetime(string='وقت الاعتماد', copy=False, readonly=True)

    rejection_reason = fields.Text(string='سبب الرفض', copy=False)
    rejected_at       = fields.Datetime(string='وقت الرفض', copy=False, readonly=True)

    posted_at = fields.Datetime(string='وقت الترحيل', copy=False, readonly=True)
    posted_ref = fields.Char(string='مرجع الجرد الفعلي', copy=False, readonly=True)

    line_ids = fields.One2many('saycare.inventory.count.request.line', 'request_id', string='أصناف الجرد', copy=True)

    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_totals')
    diff_total = fields.Float(string='صافي فرق الكميات', compute='_compute_totals', digits=(16, 3))

    @api.depends('line_ids.diff')
    def _compute_totals(self):
        for rec in self:
            rec.item_count = len(rec.line_ids)
            rec.diff_total = sum(rec.line_ids.mapped('diff'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'مسودة جديدة':
                vals['name'] = self.env['ir.sequence'].next_by_code('saycare.inventory.count.request') or 'مسودة جديدة'
        return super().create(vals_list)

    def _to_dict(self, with_lines=True):
        self.ensure_one()
        d = {
            'id':               self.id,
            'name':             self.name or '',
            'warehouseId':      self.warehouse_id.id if self.warehouse_id else None,
            'warehouseName':    self.warehouse_id.display_name if self.warehouse_id else '',
            'userId':           self.user_id.id if self.user_id else None,
            'ownerName':        self.user_id.name if self.user_id else '',
            'date':             str(self.date) if self.date else '',
            'notes':            self.notes or '',
            'state':            self.state,
            'itemCount':        self.item_count,
            'diffTotal':        self.diff_total,
            'memberUserId':     self.member_user_id.id if self.member_user_id else None,
            'memberUserName':   self.member_user_id.name if self.member_user_id else '',
            'memberApprovedAt': str(self.member_approved_at) if self.member_approved_at else '',
            'rejectionReason':  self.rejection_reason or '',
            'rejectedAt':       str(self.rejected_at) if self.rejected_at else '',
            'postedAt':         str(self.posted_at) if self.posted_at else '',
            'postedRef':        self.posted_ref or '',
            'createdAt':        str(self.create_date) if self.create_date else '',
        }
        if with_lines:
            d['lines'] = [line._to_dict() for line in self.line_ids]
        return d


class SaycareInventoryCountRequestLine(models.Model):
    _name        = 'saycare.inventory.count.request.line'
    _description = 'Inventory Count Request Line'
    _order       = 'id'

    request_id  = fields.Many2one('saycare.inventory.count.request', string='طلب الجرد',
                                   required=True, ondelete='cascade', index=True)
    product_id  = fields.Many2one('product.product', string='الصنف', required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='الموقع')
    lot_id      = fields.Many2one('stock.lot', string='رقم الدفعة')
    uom_id      = fields.Many2one('uom.uom', string='الوحدة')

    system_qty = fields.Float(string='الكمية بالنظام', digits=(16, 3))
    actual_qty = fields.Float(string='الكمية الفعلية', digits=(16, 3))
    note       = fields.Char(string='ملاحظات')

    diff = fields.Float(string='الفرق', compute='_compute_diff', store=True, digits=(16, 3))

    @api.depends('system_qty', 'actual_qty')
    def _compute_diff(self):
        for rec in self:
            rec.diff = (rec.actual_qty or 0.0) - (rec.system_qty or 0.0)

    def _to_dict(self):
        self.ensure_one()
        return {
            'id':          self.id,
            'productId':   self.product_id.id if self.product_id else None,
            'productName': self.product_id.name if self.product_id else '',
            'productCode': self.product_id.default_code or '' if self.product_id else '',
            'locationId':  self.location_id.id if self.location_id else None,
            'locationName': self.location_id.complete_name if self.location_id else '',
            'lotId':       self.lot_id.id if self.lot_id else None,
            'lotName':     self.lot_id.name if self.lot_id else '',
            'uomId':       self.uom_id.id if self.uom_id else None,
            'uomName':     self.uom_id.name if self.uom_id else '',
            'systemQty':   self.system_qty or 0.0,
            'actualQty':   self.actual_qty or 0.0,
            'diff':        self.diff or 0.0,
            'note':        self.note or '',
        }
