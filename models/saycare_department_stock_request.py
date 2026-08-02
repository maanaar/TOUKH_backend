# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


_QTY_EPSILON = 1e-6


class SaycareDepartmentStockRequest(models.Model):
    _name = 'saycare.department.stock.request'
    _description = 'Department Stock Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='رقم الطلب', default='New', copy=False, readonly=True, tracking=True)
    request_date = fields.Date(string='تاريخ الطلب', default=fields.Date.context_today, required=True, tracking=True)
    required_date = fields.Date(string='تاريخ الاحتياج', tracking=True)
    requester_employee_id = fields.Many2one(
        'hr.employee', string='طالب الاحتياج', required=True, ondelete='restrict', tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='القسم الطالب', required=True, ondelete='restrict', tracking=True,
    )
    source_warehouse_id = fields.Many2one(
        'stock.warehouse', string='المخزن المصدر', required=True, ondelete='restrict', tracking=True,
    )
    source_location_id = fields.Many2one(
        'stock.location', string='موقع المخزن المصدر', readonly=True, ondelete='restrict',
    )
    destination_location_id = fields.Many2one(
        'stock.location', string='موقع القسم المستلم', readonly=True, ondelete='restrict',
    )
    directed_user_id = fields.Many2one('res.users', string='موجه إلى', ondelete='restrict', tracking=True)
    priority = fields.Selection([
        ('normal', 'عادي'),
        ('urgent', 'عاجل'),
        ('critical', 'حرج'),
    ], string='الأولوية', default='normal', required=True, tracking=True)
    notes = fields.Text(string='سبب الطلب / الملاحظات')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مرسل للمخزن'),
        ('awaiting_receipt', 'بانتظار استلام القسم'),
        ('partially_issued', 'مصروف جزئياً'),
        ('issued', 'تم الصرف'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغى'),
    ], default='draft', copy=False, tracking=True, required=True)

    line_ids = fields.One2many(
        'saycare.department.stock.request.line', 'request_id', string='الأصناف', copy=True,
    )
    issue_ids = fields.One2many(
        'saycare.department.stock.issue', 'request_id', string='عمليات الصرف', copy=False,
    )

    submitted_by_id = fields.Many2one('res.users', string='أرسل بواسطة', readonly=True, copy=False)
    submitted_at = fields.Datetime(string='وقت الإرسال', readonly=True, copy=False)
    rejected_by_id = fields.Many2one('res.users', string='رفض بواسطة', readonly=True, copy=False)
    rejected_at = fields.Datetime(string='وقت الرفض', readonly=True, copy=False)
    rejection_reason = fields.Text(string='سبب الرفض', copy=False)

    item_count = fields.Integer(string='عدد الأصناف', compute='_compute_totals')
    requested_qty_total = fields.Float(string='إجمالي المطلوب', compute='_compute_totals')
    issued_qty_total = fields.Float(string='إجمالي المصروف', compute='_compute_totals')

    @api.depends('line_ids.requested_qty', 'line_ids.issued_qty')
    def _compute_totals(self):
        for rec in self:
            rec.item_count = len(rec.line_ids)
            rec.requested_qty_total = sum(rec.line_ids.mapped('requested_qty'))
            rec.issued_qty_total = sum(rec.line_ids.mapped('issued_qty'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'saycare.department.stock.request'
                ) or _('New')
            self._apply_locations(vals)
        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {
            'department_id', 'source_warehouse_id', 'requester_employee_id', 'line_ids',
        }
        if protected_fields.intersection(vals) and any(rec.state != 'draft' for rec in self):
            raise UserError('لا يمكن تعديل بيانات الطلب أو أصنافه بعد الإرسال')
        for rec in self:
            rec_vals = dict(vals)
            rec._apply_locations(rec_vals, current=rec)
            super(SaycareDepartmentStockRequest, rec).write(rec_vals)
        return True

    @api.model
    def _apply_locations(self, vals, current=None):
        warehouse = False
        department = False

        if vals.get('source_warehouse_id'):
            warehouse = self.env['stock.warehouse'].sudo().browse(int(vals['source_warehouse_id']))
        elif current:
            warehouse = current.source_warehouse_id

        if vals.get('department_id'):
            department = self.env['hr.department'].sudo().browse(int(vals['department_id']))
        elif current:
            department = current.department_id

        source_location = current.source_location_id if current else False
        destination_location = current.destination_location_id if current else False

        if warehouse:
            if not warehouse.exists() or not warehouse.lot_stock_id:
                raise ValidationError('المخزن المختار لا يحتوي على موقع مخزني صالح')
            source_location = warehouse.lot_stock_id
            vals['source_location_id'] = source_location.id

        if department:
            if not department.exists():
                raise ValidationError('القسم المختار غير موجود')
            destination_location = department.department_location_id
            if (
                not destination_location
                or not destination_location.exists()
                or not destination_location.active
                or destination_location.usage != 'internal'
            ):
                raise ValidationError('لا يوجد موقع مخزني داخلي فعال مخصص للقسم المختار')
            vals['destination_location_id'] = destination_location.id

        if source_location and destination_location and source_location == destination_location:
            raise ValidationError('لا يمكن أن يكون موقع المخزن المصدر هو نفس موقع القسم المستلم')

    @api.constrains('required_date', 'request_date')
    def _check_dates(self):
        for rec in self:
            if rec.required_date and rec.request_date and rec.required_date < rec.request_date:
                raise ValidationError('تاريخ الاحتياج لا يمكن أن يسبق تاريخ الطلب')

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('يمكن إرسال الطلبات المسودة فقط')
            if not rec.line_ids:
                raise ValidationError('أضف صنفاً واحداً على الأقل')
            if any(line.requested_qty <= 0 for line in rec.line_ids):
                raise ValidationError('الكمية المطلوبة يجب أن تكون أكبر من صفر')
            rec.write({
                'state': 'submitted',
                'submitted_by_id': self.env.uid,
                'submitted_at': fields.Datetime.now(),
            })
        return True

    def action_reject(self, reason):
        if not reason:
            raise ValidationError('سبب الرفض مطلوب')
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('يمكن رفض الطلب قبل بدء الصرف فقط')
            rec.write({
                'state': 'rejected',
                'rejection_reason': reason,
                'rejected_by_id': self.env.uid,
                'rejected_at': fields.Datetime.now(),
            })
        return True

    def _refresh_issue_state(self):
        for rec in self:
            if rec.state in ('rejected', 'cancelled'):
                continue
            total_requested = sum(rec.line_ids.mapped('requested_qty'))
            total_issued = sum(rec.line_ids.mapped('issued_qty'))
            if total_issued <= _QTY_EPSILON:
                rec.state = 'submitted'
            elif total_issued + _QTY_EPSILON >= total_requested:
                rec.state = 'issued'
            else:
                rec.state = 'partially_issued'


class SaycareDepartmentStockRequestLine(models.Model):
    _name = 'saycare.department.stock.request.line'
    _description = 'Department Stock Request Line'
    _order = 'id'

    request_id = fields.Many2one(
        'saycare.department.stock.request', string='الطلب', required=True,
        ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='الصنف', required=True, ondelete='restrict',
    )
    uom_id = fields.Many2one(
        'uom.uom', string='الوحدة', related='product_id.uom_id', store=True, readonly=True,
    )
    requested_qty = fields.Float(
        string='الكمية المطلوبة', required=True, digits='Product Unit of Measure',
    )
    available_qty_snapshot = fields.Float(
        string='المتاح وقت الطلب', digits='Product Unit of Measure', readonly=True,
    )
    note = fields.Char(string='ملاحظات')
    issued_qty = fields.Float(
        string='الكمية المصروفة', compute='_compute_issue_progress',
        digits='Product Unit of Measure',
    )
    remaining_qty = fields.Float(
        string='الكمية المتبقية', compute='_compute_issue_progress',
        digits='Product Unit of Measure',
    )

    @api.depends(
        'request_id.issue_ids.state',
        'request_id.issue_ids.line_ids.issued_qty',
        'request_id.issue_ids.line_ids.request_line_id',
    )
    def _compute_issue_progress(self):
        for line in self:
            issue_lines = line.request_id.issue_ids.filtered(
                lambda issue: issue.state == 'received'
            ).mapped('line_ids').filtered(
                lambda issue_line: issue_line.request_line_id == line
            )
            issued = sum(issue_lines.mapped('issued_qty'))
            line.issued_qty = issued
            line.remaining_qty = max(line.requested_qty - issued, 0.0)

    @api.constrains('requested_qty')
    def _check_requested_qty(self):
        for line in self:
            if line.requested_qty <= 0:
                raise ValidationError('الكمية المطلوبة يجب أن تكون أكبر من صفر')

    @api.constrains('request_id', 'product_id')
    def _check_duplicate_product(self):
        for line in self:
            if not line.request_id or not line.product_id:
                continue
            duplicates = line.request_id.line_ids.filtered(
                lambda item: item.product_id == line.product_id
            )
            if len(duplicates) > 1:
                raise ValidationError('لا يمكن تكرار نفس الصنف داخل الطلب')


class SaycareDepartmentStockIssue(models.Model):
    _name = 'saycare.department.stock.issue'
    _description = 'Department Stock Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='رقم إذن الصرف', default='New', copy=False, readonly=True, tracking=True)
    request_id = fields.Many2one(
        'saycare.department.stock.request', string='طلب القسم', ondelete='restrict', tracking=True,
    )
    direct_issue = fields.Boolean(string='صرف مباشر', default=False, readonly=True)
    issue_date = fields.Date(string='تاريخ الصرف', default=fields.Date.context_today, required=True)
    department_id = fields.Many2one(
        'hr.department', string='القسم المستلم', required=True, ondelete='restrict',
    )
    source_warehouse_id = fields.Many2one(
        'stock.warehouse', string='المخزن المصدر', required=True, ondelete='restrict',
    )
    source_location_id = fields.Many2one(
        'stock.location', string='موقع المصدر', required=True, readonly=True, ondelete='restrict',
    )
    destination_location_id = fields.Many2one(
        'stock.location', string='موقع القسم', required=True, readonly=True, ondelete='restrict',
    )
    recipient_employee_id = fields.Many2one(
        'hr.employee', string='مستلم القسم', required=True, ondelete='restrict',
    )
    notes = fields.Text(string='ملاحظات الصرف')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('prepared', 'جاهز للتسليم'),
        ('received', 'تم الاستلام'),
        ('cancelled', 'ملغى'),
    ], default='draft', copy=False, required=True, tracking=True)
    line_ids = fields.One2many(
        'saycare.department.stock.issue.line', 'issue_id', string='أصناف الصرف', copy=True,
    )
    picking_id = fields.Many2one(
        'stock.picking', string='التحويل الداخلي', readonly=True, copy=False, ondelete='restrict',
    )
    prepared_by_id = fields.Many2one('res.users', string='جهز بواسطة', readonly=True, copy=False)
    prepared_at = fields.Datetime(string='وقت التجهيز', readonly=True, copy=False)
    received_by_id = fields.Many2one('res.users', string='أكد الاستلام', readonly=True, copy=False)
    received_at = fields.Datetime(string='وقت الاستلام', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'saycare.department.stock.issue'
                ) or _('New')

            request_rec = self.env['saycare.department.stock.request'].sudo().browse(
                vals.get('request_id')
            ) if vals.get('request_id') else False

            if request_rec and request_rec.exists():
                vals['direct_issue'] = False
                vals.setdefault('department_id', request_rec.department_id.id)
                vals.setdefault('source_warehouse_id', request_rec.source_warehouse_id.id)
                vals.setdefault('source_location_id', request_rec.source_location_id.id)
                vals.setdefault('destination_location_id', request_rec.destination_location_id.id)
            else:
                warehouse = self.env['stock.warehouse'].sudo().browse(vals.get('source_warehouse_id'))
                department = self.env['hr.department'].sudo().browse(vals.get('department_id'))
                if not warehouse.exists() or not warehouse.lot_stock_id:
                    raise ValidationError('المخزن المصدر غير صالح')
                if not department.exists() or not department.department_location_id:
                    raise ValidationError('لا يوجد موقع مخزني مخصص للقسم المختار')
                destination = department.department_location_id
                if destination.usage != 'internal' or not destination.active:
                    raise ValidationError('موقع القسم يجب أن يكون موقعاً مخزنياً داخلياً فعالاً')
                vals['source_location_id'] = warehouse.lot_stock_id.id
                vals['destination_location_id'] = destination.id
                vals['direct_issue'] = True

            recipient = self.env['hr.employee'].sudo().browse(vals.get('recipient_employee_id'))
            department = self.env['hr.department'].sudo().browse(vals.get('department_id'))
            if not recipient.exists():
                raise ValidationError('مستلم القسم مطلوب')
            if not department.exists() or recipient.department_id != department:
                raise ValidationError('مستلم القسم يجب أن يكون تابعاً للقسم المستلم')
            if not recipient.user_id:
                raise ValidationError('يجب ربط مستلم القسم بحساب مستخدم لتأكيد الاستلام')
            if vals.get('source_location_id') == vals.get('destination_location_id'):
                raise ValidationError('موقع المصدر والوجهة لا يمكن أن يكونا متطابقين')

        return super().create(vals_list)

    @api.constrains('direct_issue', 'notes')
    def _check_direct_issue_reason(self):
        for issue in self:
            if issue.direct_issue and not (issue.notes or '').strip():
                raise ValidationError('سبب الصرف المباشر مطلوب')

    def _available_qty(self, product):
        self.ensure_one()
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', 'child_of', self.source_location_id.id),
        ])
        return sum(quants.mapped(lambda quant: quant.quantity - quant.reserved_quantity))

    def action_prepare(self):
        for issue in self:
            if issue.state != 'draft':
                raise UserError('يمكن تجهيز إذن الصرف المسودة فقط')
            if not issue.line_ids:
                raise ValidationError('أضف صنفاً واحداً على الأقل')
            if issue.source_location_id == issue.destination_location_id:
                raise ValidationError('موقع المصدر والوجهة لا يمكن أن يكونا متطابقين')
            if issue.request_id and issue.request_id.state not in ('submitted', 'partially_issued'):
                raise UserError('الطلب غير متاح للتجهيز في حالته الحالية')

            for line in issue.line_ids:
                if line.issued_qty <= 0:
                    raise ValidationError('الكمية المصروفة يجب أن تكون أكبر من صفر')
                if (
                    line.request_line_id
                    and line.issued_qty > line.request_line_id.remaining_qty + _QTY_EPSILON
                ):
                    raise ValidationError('الكمية المصروفة تتجاوز الكمية المتبقية في الطلب')
                available = issue._available_qty(line.product_id)
                if line.issued_qty > available + _QTY_EPSILON:
                    raise ValidationError('الرصيد غير كاف للصنف: %s' % line.product_id.display_name)
                line.available_qty_snapshot = available

            picking_type = issue.source_warehouse_id.int_type_id
            if not picking_type:
                raise ValidationError('لا يوجد نوع تحويل داخلي للمخزن المختار')

            picking = self.env['stock.picking'].sudo().create({
                'picking_type_id': picking_type.id,
                'location_id': issue.source_location_id.id,
                'location_dest_id': issue.destination_location_id.id,
                'origin': issue.request_id.name if issue.request_id else issue.name,
                'note': issue.notes or '',
                'scheduled_date': fields.Datetime.now(),
                'move_ids': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.issued_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': issue.source_location_id.id,
                    'location_dest_id': issue.destination_location_id.id,
                }) for line in issue.line_ids],
            })
            picking.action_confirm()
            picking.action_assign()

            if picking.state != 'assigned':
                raise ValidationError('تعذر حجز كل الكميات المطلوبة من المخزن المصدر')

            issue.write({
                'picking_id': picking.id,
                'state': 'prepared',
                'prepared_by_id': self.env.uid,
                'prepared_at': fields.Datetime.now(),
            })
            if issue.request_id:
                issue.request_id.state = 'awaiting_receipt'
        return True

    def action_receive(self):
        for issue in self:
            if issue.state == 'received':
                continue
            if issue.state != 'prepared' or not issue.picking_id:
                raise UserError('يجب تجهيز إذن الصرف قبل تأكيد الاستلام')

            current_employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', self.env.uid),
            ], limit=1)
            if (
                not self.env.user.has_group('base.group_system')
                and current_employee != issue.recipient_employee_id
            ):
                raise UserError('تأكيد الاستلام متاح لمستلم القسم المحدد فقط')

            picking = issue.picking_id.sudo()
            if picking.state == 'cancel':
                raise UserError('التحويل الداخلي ملغى')
            if picking.state != 'done':
                picking.action_assign()
                if picking.state != 'assigned':
                    raise ValidationError('لم تعد كل الكميات محجوزة لإذن الصرف')
                for line in issue.line_ids:
                    move = picking.move_ids.filtered(
                        lambda item: item.product_id == line.product_id
                    )[:1]
                    if not move:
                        raise ValidationError(
                            'تعذر العثور على حركة الصنف: %s' % line.product_id.display_name
                        )
                    move.quantity = line.issued_qty

                result = picking.with_context(
                    skip_backorder=True,
                    skip_sms=True,
                    skip_immediate=True,
                    picking_ids_not_to_backorder=picking.ids,
                ).button_validate()
                if isinstance(result, dict) and result.get('res_model'):
                    picking._action_done()

            issue.write({
                'state': 'received',
                'received_by_id': self.env.uid,
                'received_at': fields.Datetime.now(),
            })
            if issue.request_id:
                issue.request_id._refresh_issue_state()
        return True


class SaycareDepartmentStockIssueLine(models.Model):
    _name = 'saycare.department.stock.issue.line'
    _description = 'Department Stock Issue Line'
    _order = 'id'

    issue_id = fields.Many2one(
        'saycare.department.stock.issue', string='إذن الصرف', required=True,
        ondelete='cascade', index=True,
    )
    request_line_id = fields.Many2one(
        'saycare.department.stock.request.line', string='سطر الطلب', ondelete='restrict',
    )
    product_id = fields.Many2one(
        'product.product', string='الصنف', required=True, ondelete='restrict',
    )
    uom_id = fields.Many2one(
        'uom.uom', string='الوحدة', related='product_id.uom_id', store=True, readonly=True,
    )
    requested_qty_snapshot = fields.Float(
        string='المطلوب', digits='Product Unit of Measure', readonly=True,
    )
    available_qty_snapshot = fields.Float(
        string='المتاح عند التجهيز', digits='Product Unit of Measure', readonly=True,
    )
    issued_qty = fields.Float(
        string='الكمية المصروفة', required=True, digits='Product Unit of Measure',
    )
    note = fields.Char(string='ملاحظات')

    @api.constrains('issued_qty')
    def _check_issued_qty(self):
        for line in self:
            if line.issued_qty <= 0:
                raise ValidationError('الكمية المصروفة يجب أن تكون أكبر من صفر')

    @api.constrains('issue_id', 'product_id')
    def _check_duplicate_product(self):
        for line in self:
            if not line.issue_id or not line.product_id:
                continue
            duplicates = line.issue_id.line_ids.filtered(
                lambda item: item.product_id == line.product_id
            )
            if len(duplicates) > 1:
                raise ValidationError('لا يمكن تكرار نفس الصنف داخل إذن الصرف')
