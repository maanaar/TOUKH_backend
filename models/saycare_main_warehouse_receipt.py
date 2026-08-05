# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class SaycareMainWarehouseReceipt(models.Model):
    _name = 'saycare.main.warehouse.receipt'
    _description = 'Main Warehouse Inspection and Addition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='رقم محضر الفحص', default='New', copy=False, readonly=True,
        tracking=True, index=True,
    )
    addition_number = fields.Char(
        string='رقم إذن الإضافة', default='New', copy=False, readonly=True,
        tracking=True, index=True,
    )
    state = fields.Selection([
        ('draft', 'مسودة الفحص'),
        ('awaiting_addition', 'بانتظار إذن الإضافة'),
        ('done', 'تمت الإضافة للمخزون'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغى'),
    ], string='الحالة', default='draft', required=True, copy=False,
        tracking=True, index=True)

    source_type = fields.Selection([
        ('purchase_order', 'أمر شراء'),
        ('direct', 'إضافة مباشرة'),
    ], string='نوع المصدر', default='purchase_order', required=True, tracking=True)
    purchase_order_id = fields.Many2one(
        'purchase.order', string='أمر الشراء', ondelete='restrict', tracking=True,
    )
    origin_reference = fields.Char(string='مرجع التوريد', tracking=True, index=True)
    supplier_id = fields.Many2one(
        'res.partner', string='المورد / المصدر',
        domain=[('supplier_rank', '>', 0)], ondelete='restrict', tracking=True,
    )
    source_description = fields.Char(string='وارد من', tracking=True)
    supplier_invoice_number = fields.Char(
        string='رقم فاتورة المورد', tracking=True, index=True,
    )
    supplier_invoice_date = fields.Date(string='تاريخ فاتورة المورد')
    receipt_date = fields.Date(
        string='تاريخ الاستلام', default=fields.Date.context_today,
        required=True, tracking=True, index=True,
    )
    receiver_employee_id = fields.Many2one(
        'hr.employee', string='مستلم البضاعة', required=True,
        ondelete='restrict', tracking=True,
    )
    destination_location_id = fields.Many2one(
        'stock.location', string='المخزن المستلم', required=True,
        domain=[('usage', '=', 'internal')], ondelete='restrict', tracking=True,
    )
    supply_type = fields.Selection([
        ('normal', 'توريد عادي'),
        ('return', 'توريد مرتجع'),
        ('donation', 'هبة / تبرع'),
        ('opening', 'رصيد افتتاحي'),
        ('adjustment', 'تسوية'),
    ], string='نوع التوريد', default='normal', required=True, tracking=True)
    notes = fields.Text(string='ملاحظات')

    line_ids = fields.One2many(
        'saycare.main.warehouse.receipt.line', 'receipt_id',
        string='الأصناف', copy=True,
    )
    picking_id = fields.Many2one(
        'stock.picking', string='حركة الاستلام', readonly=True,
        copy=False, ondelete='restrict',
    )
    inspection_approved_by_id = fields.Many2one(
        'res.users', string='اعتمد الفحص بواسطة', readonly=True, copy=False,
    )
    inspection_approved_at = fields.Datetime(
        string='وقت اعتماد الفحص', readonly=True, copy=False,
    )
    addition_approved_by_id = fields.Many2one(
        'res.users', string='اعتمد الإضافة بواسطة', readonly=True, copy=False,
    )
    addition_approved_at = fields.Datetime(
        string='وقت اعتماد الإضافة', readonly=True, copy=False,
    )
    rejection_reason = fields.Text(string='سبب الرفض', readonly=True, copy=False)

    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_totals', store=True)
    requested_qty_total = fields.Float(
        string='إجمالي المطلوب', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    received_qty_total = fields.Float(
        string='إجمالي الوارد', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    accepted_qty_total = fields.Float(
        string='إجمالي المقبول', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    rejected_qty_total = fields.Float(
        string='إجمالي المرفوض', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    amount_total = fields.Monetary(
        string='إجمالي القيمة', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='العملة',
        default=lambda self: self.env.company.currency_id, required=True,
    )

    @api.depends(
        'line_ids', 'line_ids.requested_qty', 'line_ids.received_qty',
        'line_ids.accepted_qty', 'line_ids.rejected_qty', 'line_ids.unit_price',
    )
    def _compute_totals(self):
        for receipt in self:
            receipt.item_count = len(receipt.line_ids)
            receipt.requested_qty_total = sum(receipt.line_ids.mapped('requested_qty'))
            receipt.received_qty_total = sum(receipt.line_ids.mapped('received_qty'))
            receipt.accepted_qty_total = sum(receipt.line_ids.mapped('accepted_qty'))
            receipt.rejected_qty_total = sum(receipt.line_ids.mapped('rejected_qty'))
            receipt.amount_total = sum(
                line.accepted_qty * line.unit_price for line in receipt.line_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'saycare.main.warehouse.receipt'
                    ) or 'New'
                )
        return super().create(vals_list)

    def write(self, vals):
        editable_fields = {
            'source_type', 'purchase_order_id', 'origin_reference',
            'supplier_id', 'source_description', 'supplier_invoice_number',
            'supplier_invoice_date', 'receipt_date', 'receiver_employee_id',
            'destination_location_id', 'supply_type', 'notes', 'line_ids',
            'currency_id',
        }
        if editable_fields.intersection(vals):
            locked = self.filtered(lambda rec: rec.state != 'draft')
            if locked:
                raise UserError('لا يمكن تعديل بيانات الفحص بعد اعتماده')
        return super().write(vals)

    def _validate_source(self):
        self.ensure_one()
        if self.source_type == 'purchase_order':
            if not self.purchase_order_id and not (self.origin_reference or '').strip():
                raise ValidationError('حدد أمر الشراء أو مرجع التوريد')
        elif not (self.source_description or '').strip():
            raise ValidationError('حدد مصدر الإضافة المباشرة')

    def _validate_inspection(self):
        self.ensure_one()
        if self.destination_location_id.usage != 'internal':
            raise ValidationError('المخزن المستلم يجب أن يكون موقعاً داخلياً')
        if not self.line_ids:
            raise ValidationError('أضف صنفاً واحداً على الأقل')
        self._validate_source()
        for line in self.line_ids:
            if line.received_qty <= 0:
                raise ValidationError(
                    'الكمية الواردة يجب أن تكون أكبر من صفر للصنف: %s'
                    % line.product_id.display_name
                )
            classified = line.accepted_qty + line.rejected_qty
            if float_compare(
                classified, line.received_qty,
                precision_rounding=line.uom_id.rounding,
            ) != 0:
                raise ValidationError(
                    'يجب توزيع كامل الكمية الواردة إلى مقبول ومرفوض للصنف: %s'
                    % line.product_id.display_name
                )
            line._validate_tracking_batches()

    def action_approve_inspection(self):
        for receipt in self:
            if receipt.state != 'draft':
                raise UserError('يمكن اعتماد محضر الفحص المسودة فقط')
            receipt._validate_inspection()
            receipt.write({
                'state': 'awaiting_addition',
                'inspection_approved_by_id': self.env.uid,
                'inspection_approved_at': fields.Datetime.now(),
                'rejection_reason': False,
            })
        return True

    def action_reject_inspection(self, reason):
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError('سبب الرفض مطلوب')
        for receipt in self:
            if receipt.state != 'draft':
                raise UserError('يمكن رفض محضر الفحص المسودة فقط')
            receipt.write({
                'state': 'rejected',
                'rejection_reason': reason,
                'inspection_approved_by_id': self.env.uid,
                'inspection_approved_at': fields.Datetime.now(),
            })
        return True

    def _find_incoming_picking_type(self):
        self.ensure_one()
        PickingType = self.env['stock.picking.type'].sudo()
        picking_type = PickingType.search([
            ('code', '=', 'incoming'),
            ('default_location_dest_id', 'child_of', self.destination_location_id.id),
        ], limit=1)
        if not picking_type:
            picking_type = PickingType.search([('code', '=', 'incoming')], limit=1)
        if not picking_type:
            raise ValidationError('لا يوجد نوع استلام مخزني معرف')
        return picking_type

    def _supplier_location(self, picking_type):
        self.ensure_one()
        source = picking_type.default_location_src_id
        if not source or source.usage != 'supplier':
            source = self.env['stock.location'].sudo().search([
                ('usage', '=', 'supplier'),
                ('company_id', 'in', [False, self.env.company.id]),
            ], limit=1)
        if not source:
            raise ValidationError('لا يوجد موقع مورد معرف لحركة الاستلام')
        return source

    def _prepare_picking_quantities(self, picking):
        self.ensure_one()
        accepted_lines = self.line_ids.filtered(
            lambda line: not float_is_zero(
                line.accepted_qty, precision_rounding=line.uom_id.rounding,
            )
        )
        for line in accepted_lines:
            move = picking.move_ids.filtered(
                lambda candidate: candidate.product_id == line.product_id
            )[:1]
            if not move:
                raise ValidationError(
                    'تعذر العثور على حركة الصنف: %s'
                    % line.product_id.display_name
                )
            if line.product_id.tracking == 'none':
                move.quantity = line.accepted_qty
                continue

            move.move_line_ids.unlink()
            for batch in line.batch_ids:
                lot = self.env['stock.lot'].sudo().search([
                    ('name', '=', batch.batch_number),
                    ('product_id', '=', line.product_id.id),
                    ('company_id', 'in', [False, picking.company_id.id]),
                ], limit=1)
                if not lot:
                    lot_values = {
                        'name': batch.batch_number,
                        'product_id': line.product_id.id,
                        'company_id': picking.company_id.id,
                    }
                    if batch.expiry_date and 'expiration_date' in self.env['stock.lot']._fields:
                        lot_values['expiration_date'] = fields.Datetime.to_datetime(
                            '%s 23:59:59' % batch.expiry_date
                        )
                    lot = self.env['stock.lot'].sudo().create(lot_values)
                self.env['stock.move.line'].sudo().create({
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'lot_id': lot.id,
                    'quantity': batch.quantity,
                })

    def action_finalize_addition(self):
        for receipt in self:
            self.env.cr.execute(
                'SELECT id FROM %s WHERE id = %%s FOR UPDATE' % receipt._table,
                [receipt.id],
            )
            receipt.invalidate_recordset()
            if receipt.state == 'done':
                if receipt.picking_id and receipt.picking_id.state == 'done':
                    continue
                raise UserError('إذن الإضافة مكتمل ولكن حركة المخزون غير مكتملة')
            if receipt.state != 'awaiting_addition':
                raise UserError('يجب اعتماد الفحص قبل إصدار إذن الإضافة')

            accepted_lines = receipt.line_ids.filtered(
                lambda line: not float_is_zero(
                    line.accepted_qty, precision_rounding=line.uom_id.rounding,
                )
            )
            if not accepted_lines:
                raise ValidationError('لا توجد كميات مقبولة لإضافتها للمخزون')

            picking = receipt.picking_id.sudo()
            if not picking:
                picking_type = receipt._find_incoming_picking_type()
                source_location = receipt._supplier_location(picking_type)
                origin = (
                    receipt.purchase_order_id.name
                    or receipt.origin_reference
                    or receipt.name
                )
                picking = self.env['stock.picking'].sudo().create({
                    'picking_type_id': picking_type.id,
                    'location_id': source_location.id,
                    'location_dest_id': receipt.destination_location_id.id,
                    'origin': origin,
                    'partner_id': receipt.supplier_id.id or False,
                    'scheduled_date': fields.Datetime.now(),
                    'note': receipt.notes or '',
                    'move_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.accepted_qty,
                        'product_uom': line.uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': receipt.destination_location_id.id,
                    }) for line in accepted_lines],
                })
                receipt.picking_id = picking.id

            if picking.state == 'cancel':
                raise UserError('حركة الاستلام ملغاة')
            if picking.state != 'done':
                if picking.state == 'draft':
                    picking.action_confirm()
                picking.action_assign()
                receipt._prepare_picking_quantities(picking)
                result = picking.with_context(
                    skip_backorder=True,
                    skip_sms=True,
                    skip_immediate=True,
                    picking_ids_not_to_backorder=picking.ids,
                ).button_validate()
                if isinstance(result, dict) and result.get('res_model'):
                    picking._action_done()
            if picking.state != 'done':
                raise ValidationError('تعذر إكمال حركة الإضافة للمخزون')

            addition_number = receipt.addition_number
            if addition_number == 'New':
                addition_number = (
                    self.env['ir.sequence'].next_by_code(
                        'saycare.main.warehouse.addition'
                    ) or 'New'
                )
            receipt.write({
                'addition_number': addition_number,
                'state': 'done',
                'addition_approved_by_id': self.env.uid,
                'addition_approved_at': fields.Datetime.now(),
            })
        return True


class SaycareMainWarehouseReceiptLine(models.Model):
    _name = 'saycare.main.warehouse.receipt.line'
    _description = 'Main Warehouse Receipt Line'
    _order = 'id'

    receipt_id = fields.Many2one(
        'saycare.main.warehouse.receipt', string='محضر الفحص', required=True,
        ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='الصنف', required=True, ondelete='restrict',
    )
    uom_id = fields.Many2one(
        'uom.uom', string='الوحدة', related='product_id.uom_id',
        store=True, readonly=True,
    )
    requested_qty = fields.Float(
        string='الكمية المطلوبة', digits='Product Unit of Measure', default=0,
    )
    received_qty = fields.Float(
        string='الكمية الواردة', digits='Product Unit of Measure', required=True,
    )
    accepted_qty = fields.Float(
        string='الكمية المقبولة', digits='Product Unit of Measure', required=True,
    )
    rejected_qty = fields.Float(
        string='الكمية المرفوضة', digits='Product Unit of Measure', default=0,
    )
    unit_price = fields.Float(string='سعر الوحدة', digits='Product Price', default=0)
    quality_status = fields.Selection([
        ('accepted', 'مطابق'),
        ('conditional', 'مقبول بملاحظات'),
        ('rejected', 'مرفوض'),
    ], string='حالة الفحص', default='accepted', required=True)
    storage_location_note = fields.Char(string='موقع التخزين')
    notes = fields.Char(string='ملاحظات')
    batch_ids = fields.One2many(
        'saycare.main.warehouse.receipt.batch', 'receipt_line_id',
        string='الدفعات', copy=True,
    )

    @api.constrains(
        'requested_qty', 'received_qty', 'accepted_qty',
        'rejected_qty', 'unit_price',
    )
    def _check_quantities(self):
        for line in self:
            values = [
                line.requested_qty, line.received_qty, line.accepted_qty,
                line.rejected_qty, line.unit_price,
            ]
            if any(value < 0 for value in values):
                raise ValidationError('الكميات والأسعار لا يمكن أن تكون سالبة')
            if float_compare(
                line.accepted_qty + line.rejected_qty,
                line.received_qty,
                precision_rounding=line.uom_id.rounding,
            ) > 0:
                raise ValidationError('المقبول والمرفوض يتجاوزان الكمية الواردة')

    @api.constrains('receipt_id', 'product_id')
    def _check_duplicate_product(self):
        for line in self:
            if not line.receipt_id or not line.product_id:
                continue
            duplicates = line.receipt_id.line_ids.filtered(
                lambda candidate: candidate.product_id == line.product_id
            )
            if len(duplicates) > 1:
                raise ValidationError('لا يمكن تكرار نفس الصنف داخل محضر الفحص')

    def _validate_tracking_batches(self):
        self.ensure_one()
        if self.product_id.tracking == 'none':
            return
        if float_is_zero(
            self.accepted_qty, precision_rounding=self.uom_id.rounding,
        ):
            return
        if not self.batch_ids:
            raise ValidationError(
                'بيانات الدفعة مطلوبة للصنف المتتبع: %s'
                % self.product_id.display_name
            )
        batch_total = sum(self.batch_ids.mapped('quantity'))
        if float_compare(
            batch_total, self.accepted_qty,
            precision_rounding=self.uom_id.rounding,
        ) != 0:
            raise ValidationError(
                'إجمالي كميات الدفعات يجب أن يساوي الكمية المقبولة للصنف: %s'
                % self.product_id.display_name
            )
        if self.product_id.tracking == 'serial' and any(
            float_compare(
                batch.quantity, 1.0,
                precision_rounding=self.uom_id.rounding,
            ) != 0
            for batch in self.batch_ids
        ):
            raise ValidationError('كل رقم مسلسل يجب أن تكون كميته واحداً')


class SaycareMainWarehouseReceiptBatch(models.Model):
    _name = 'saycare.main.warehouse.receipt.batch'
    _description = 'Main Warehouse Receipt Batch'
    _order = 'id'

    receipt_line_id = fields.Many2one(
        'saycare.main.warehouse.receipt.line', string='سطر الاستلام',
        required=True, ondelete='cascade', index=True,
    )
    batch_number = fields.Char(
        string='رقم الدفعة / المسلسل', required=True, index=True,
    )
    lot_number = fields.Char(string='رقم التشغيلة')
    manufacturing_date = fields.Date(string='تاريخ الإنتاج')
    expiry_date = fields.Date(string='تاريخ الصلاحية')
    quantity = fields.Float(
        string='الكمية', required=True, digits='Product Unit of Measure',
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for batch in self:
            if batch.quantity <= 0:
                raise ValidationError('كمية الدفعة يجب أن تكون أكبر من صفر')
