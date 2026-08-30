# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class SaycareMainWarehouseReceipt(models.Model):
    _name = 'saycare.main.warehouse.receipt'
    _description = 'Main Warehouse Addition Receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Legacy inspection number is retained for historical compatibility.
    name = fields.Char(
        string='Ø±Ù‚Ù… Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ', default='New', copy=False, readonly=True,
        tracking=True, index=True,
    )
    addition_number = fields.Char(
        string='Ø±Ù‚Ù… Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©', default='New', copy=False, readonly=True,
        tracking=True, index=True,
    )
    state = fields.Selection([
        ('draft', 'Ù…Ø³ÙˆØ¯Ø©'),
        ('awaiting_addition', 'Ø¨Ø§Ù†ØªØ¸Ø§Ø± Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©'),  # legacy state
        ('done', 'ØªÙ…Øª Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ù„Ù„Ù…Ø®Ø²ÙˆÙ†'),
        ('rejected', 'Ù…Ø±ÙÙˆØ¶'),  # legacy state
        ('cancelled', 'Ù…Ù„ØºÙ‰'),
    ], string='Ø§Ù„Ø­Ø§Ù„Ø©', default='draft', required=True, copy=False,
        tracking=True, index=True)

    # New addition-voucher header fields.
    priced_delivery_number = fields.Char(
        string='Ø±Ù‚Ù… ØªØ³Ù„ÙŠÙ… Ù…Ø³Ø¹Ù‘Ø± (Ù…Ø³ØªØ®Ù„ØµØ§Øª)', tracking=True, index=True,
    )
    supplier_number = fields.Char(string='Ø±Ù‚Ù… Ø§Ù„Ù…ÙˆØ±Ø¯', tracking=True, index=True)
    statement_type = fields.Char(string='Ù†ÙˆØ¹ Ø§Ù„Ù…Ø³ØªØ®Ù„Øµ', tracking=True)
    supply_request_reference = fields.Char(string='Ø·Ù„Ø¨ Ø§Ù„Ø¥Ù…Ø¯Ø§Ø¯', tracking=True, index=True)
    supply_order_reference = fields.Char(string='Ø£Ù…Ø± Ø§Ù„ØªÙˆØ±ÙŠØ¯', tracking=True, index=True)
    issue_date = fields.Date(
        string='ØªØ§Ø±ÙŠØ® Ø¥ØµØ¯Ø§Ø± Ø§Ù„Ø¥Ø°Ù†', default=fields.Date.context_today,
        required=True, tracking=True, index=True,
    )
    inspection_attachment_ids = fields.Many2many(
        'ir.attachment',
        'saycare_mwr_inspection_attachment_rel',
        'receipt_id', 'attachment_id',
        string='Ù…Ø±ÙÙ‚Ø§Øª Ø§Ù„ÙØ­Øµ',
        copy=False,
    )

    # Legacy/source fields are preserved so existing records and callers keep working.
    source_type = fields.Selection([
        ('purchase_order', 'Ø£Ù…Ø± Ø´Ø±Ø§Ø¡'),
        ('direct', 'Ø¥Ø¶Ø§ÙØ© Ù…Ø¨Ø§Ø´Ø±Ø©'),
    ], string='Ù†ÙˆØ¹ Ø§Ù„Ù…ØµØ¯Ø±', default='purchase_order', required=True, tracking=True)
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Ø£Ù…Ø± Ø§Ù„Ø´Ø±Ø§Ø¡', ondelete='restrict', tracking=True,
    )
    origin_reference = fields.Char(string='Ù…Ø±Ø¬Ø¹ Ø§Ù„ØªÙˆØ±ÙŠØ¯', tracking=True, index=True)
    supplier_id = fields.Many2one(
        'res.partner', string='Ø§Ù„Ù…ÙˆØ±Ø¯ / Ø§Ù„Ù…ØµØ¯Ø±',
        domain=[('supplier_rank', '>', 0)], ondelete='restrict', tracking=True,
    )
    source_description = fields.Char(string='ÙˆØ§Ø±Ø¯ Ù…Ù†', tracking=True)
    supplier_invoice_number = fields.Char(
        string='Ø±Ù‚Ù… ÙØ§ØªÙˆØ±Ø© Ø§Ù„Ù…ÙˆØ±Ø¯', tracking=True, index=True,
    )
    supplier_invoice_date = fields.Date(string='ØªØ§Ø±ÙŠØ® ÙØ§ØªÙˆØ±Ø© Ø§Ù„Ù…ÙˆØ±Ø¯')
    receipt_date = fields.Date(
        string='ØªØ§Ø±ÙŠØ® Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù…', default=fields.Date.context_today,
        required=True, tracking=True, index=True,
    )
    receiver_employee_id = fields.Many2one(
        'hr.employee', string='Ù…Ø³ØªÙ„Ù… Ø§Ù„Ø¨Ø¶Ø§Ø¹Ø©',
        ondelete='restrict', tracking=True,
    )
    destination_location_id = fields.Many2one(
        'stock.location', string='Ø§Ù„Ù…Ø®Ø²Ù† Ø§Ù„Ù…Ø³ØªÙ„Ù…', required=True,
        domain=[('usage', '=', 'internal')], ondelete='restrict', tracking=True,
    )
    supply_type = fields.Selection([
        ('normal', 'ØªÙˆØ±ÙŠØ¯ Ø¹Ø§Ø¯ÙŠ'),
        ('return', 'ØªÙˆØ±ÙŠØ¯ Ù…Ø±ØªØ¬Ø¹'),
        ('donation', 'Ù‡Ø¨Ø© / ØªØ¨Ø±Ø¹'),
        ('opening', 'Ø±ØµÙŠØ¯ Ø§ÙØªØªØ§Ø­ÙŠ'),
        ('adjustment', 'ØªØ³ÙˆÙŠØ©'),
    ], string='Ù†ÙˆØ¹ Ø§Ù„ØªÙˆØ±ÙŠØ¯', default='normal', required=True, tracking=True)
    notes = fields.Text(string='Ù…Ù„Ø§Ø­Ø¸Ø§Øª')

    line_ids = fields.One2many(
        'saycare.main.warehouse.receipt.line', 'receipt_id',
        string='Ø§Ù„Ø£ØµÙ†Ø§Ù', copy=True,
    )
    picking_id = fields.Many2one(
        'stock.picking', string='Ø­Ø±ÙƒØ© Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù…', readonly=True,
        copy=False, ondelete='restrict',
    )

    # Legacy inspection audit remains readable.
    inspection_approved_by_id = fields.Many2one(
        'res.users', string='Ø§Ø¹ØªÙ…Ø¯ Ø§Ù„ÙØ­Øµ Ø¨ÙˆØ§Ø³Ø·Ø©', readonly=True, copy=False,
    )
    inspection_approved_at = fields.Datetime(
        string='ÙˆÙ‚Øª Ø§Ø¹ØªÙ…Ø§Ø¯ Ø§Ù„ÙØ­Øµ', readonly=True, copy=False,
    )
    addition_approved_by_id = fields.Many2one(
        'res.users', string='Ø§Ø¹ØªÙ…Ø¯ Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ø¨ÙˆØ§Ø³Ø·Ø©', readonly=True, copy=False,
    )
    addition_approved_at = fields.Datetime(
        string='ÙˆÙ‚Øª Ø§Ø¹ØªÙ…Ø§Ø¯ Ø§Ù„Ø¥Ø¶Ø§ÙØ©', readonly=True, copy=False,
    )
    rejection_reason = fields.Text(string='Ø³Ø¨Ø¨ Ø§Ù„Ø±ÙØ¶', readonly=True, copy=False)

    item_count = fields.Integer(string='Ø¹Ø¯Ø¯ Ø§Ù„Ø£ØµÙ†Ø§Ù', compute='_compute_totals', store=True)
    requested_qty_total = fields.Float(
        string='Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø·Ù„ÙˆØ¨', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    received_qty_total = fields.Float(
        string='Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„ÙˆØ§Ø±Ø¯', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    accepted_qty_total = fields.Float(
        string='Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø¶Ø§Ù', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    rejected_qty_total = fields.Float(
        string='Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø±ÙÙˆØ¶', compute='_compute_totals', store=True,
        digits='Product Unit of Measure',
    )
    amount_total = fields.Monetary(
        string='Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù‚ÙŠÙ…Ø©', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Ø§Ù„Ø¹Ù…Ù„Ø©',
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
        Partner = self.env['res.partner'].sudo()
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'saycare.main.warehouse.receipt'
                    ) or 'New'
                )
            if vals.get('addition_number', 'New') == 'New':
                vals['addition_number'] = (
                    self.env['ir.sequence'].next_by_code(
                        'saycare.main.warehouse.addition'
                    ) or 'New'
                )
            if vals.get('supplier_id') and not (vals.get('supplier_number') or '').strip():
                supplier = Partner.browse(vals['supplier_id'])
                if supplier.exists() and supplier.ref:
                    vals['supplier_number'] = supplier.ref
            if vals.get('issue_date') and not vals.get('receipt_date'):
                vals['receipt_date'] = vals['issue_date']
            elif vals.get('receipt_date') and not vals.get('issue_date'):
                vals['issue_date'] = vals['receipt_date']
        return super().create(vals_list)

    def write(self, vals):
        editable_fields = {
            'priced_delivery_number', 'supplier_number', 'statement_type',
            'supply_request_reference', 'supply_order_reference', 'issue_date',
            'inspection_attachment_ids',
            'source_type', 'purchase_order_id', 'origin_reference',
            'supplier_id', 'source_description', 'supplier_invoice_number',
            'supplier_invoice_date', 'receipt_date', 'receiver_employee_id',
            'destination_location_id', 'supply_type', 'notes', 'line_ids',
            'currency_id',
        }
        if editable_fields.intersection(vals):
            non_attachment_fields = editable_fields - {'inspection_attachment_ids'}
            if non_attachment_fields.intersection(vals):
                locked = self.filtered(lambda rec: rec.state != 'draft')
                if locked:
                    raise UserError('Ù„Ø§ ÙŠÙ…ÙƒÙ† ØªØ¹Ø¯ÙŠÙ„ Ø¨ÙŠØ§Ù†Ø§Øª Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ø¨Ø¹Ø¯ Ø§Ø¹ØªÙ…Ø§Ø¯Ù‡')

        if 'supplier_id' in vals and 'supplier_number' not in vals:
            supplier = self.env['res.partner'].sudo().browse(vals.get('supplier_id'))
            vals['supplier_number'] = supplier.ref if supplier.exists() and supplier.ref else False

        if vals.get('issue_date') and 'receipt_date' not in vals:
            vals['receipt_date'] = vals['issue_date']
        elif vals.get('receipt_date') and 'issue_date' not in vals:
            vals['issue_date'] = vals['receipt_date']

        return super().write(vals)

    def _validate_source(self):
        """Legacy inspection validation only."""
        self.ensure_one()
        if self.source_type == 'purchase_order':
            if not self.purchase_order_id and not (self.origin_reference or '').strip():
                raise ValidationError('Ø­Ø¯Ø¯ Ø£Ù…Ø± Ø§Ù„Ø´Ø±Ø§Ø¡ Ø£Ùˆ Ù…Ø±Ø¬Ø¹ Ø§Ù„ØªÙˆØ±ÙŠØ¯')
        elif not (self.source_description or '').strip():
            raise ValidationError('Ø­Ø¯Ø¯ Ù…ØµØ¯Ø± Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ø§Ù„Ù…Ø¨Ø§Ø´Ø±Ø©')

    def _validate_inspection(self):
        """Legacy two-step inspection flow retained for historical callers."""
        self.ensure_one()
        if self.destination_location_id.usage != 'internal':
            raise ValidationError('Ø§Ù„Ù…Ø®Ø²Ù† Ø§Ù„Ù…Ø³ØªÙ„Ù… ÙŠØ¬Ø¨ Ø£Ù† ÙŠÙƒÙˆÙ† Ù…ÙˆÙ‚Ø¹Ø§Ù‹ Ø¯Ø§Ø®Ù„ÙŠØ§Ù‹')
        if not self.line_ids:
            raise ValidationError('Ø£Ø¶Ù ØµÙ†ÙØ§Ù‹ ÙˆØ§Ø­Ø¯Ø§Ù‹ Ø¹Ù„Ù‰ Ø§Ù„Ø£Ù‚Ù„')
        self._validate_source()
        for line in self.line_ids:
            if line.received_qty <= 0:
                raise ValidationError(
                    'Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„ÙˆØ§Ø±Ø¯Ø© ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† Ø£ÙƒØ¨Ø± Ù…Ù† ØµÙØ± Ù„Ù„ØµÙ†Ù: %s'
                    % line.product_id.display_name
                )
            classified = line.accepted_qty + line.rejected_qty
            if float_compare(
                classified, line.received_qty,
                precision_rounding=line.uom_id.rounding,
            ) != 0:
                raise ValidationError(
                    'ÙŠØ¬Ø¨ ØªÙˆØ²ÙŠØ¹ ÙƒØ§Ù…Ù„ Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„ÙˆØ§Ø±Ø¯Ø© Ø¥Ù„Ù‰ Ù…Ù‚Ø¨ÙˆÙ„ ÙˆÙ…Ø±ÙÙˆØ¶ Ù„Ù„ØµÙ†Ù: %s'
                    % line.product_id.display_name
                )
            line._validate_tracking_batches(line.accepted_qty)

    def _validate_addition(self):
        self.ensure_one()
        if self.destination_location_id.usage != 'internal':
            raise ValidationError('Ø§Ù„Ù…Ø®Ø²Ù† Ø§Ù„Ù…Ø³ØªÙ„Ù… ÙŠØ¬Ø¨ Ø£Ù† ÙŠÙƒÙˆÙ† Ù…ÙˆÙ‚Ø¹Ø§Ù‹ Ø¯Ø§Ø®Ù„ÙŠØ§Ù‹')
        if not self.line_ids:
            raise ValidationError('Ø£Ø¶Ù ØµÙ†ÙØ§Ù‹ ÙˆØ§Ø­Ø¯Ø§Ù‹ Ø¹Ù„Ù‰ Ø§Ù„Ø£Ù‚Ù„')

        for line in self.line_ids:
            addition_qty = line._addition_qty()
            if float_compare(
                addition_qty, 0.0, precision_rounding=line.uom_id.rounding,
            ) <= 0:
                raise ValidationError(
                    'Ø§Ù„ÙƒÙ…ÙŠØ© Ù…Ø¹ Ø§Ù„Ø¨ÙˆÙ†Øµ ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† Ø£ÙƒØ¨Ø± Ù…Ù† ØµÙØ± Ù„Ù„ØµÙ†Ù: %s'
                    % line.product_id.display_name
                )
            if (
                line.manufacturing_date and line.expiry_date
                and line.expiry_date < line.manufacturing_date
            ):
                raise ValidationError(
                    'ØªØ§Ø±ÙŠØ® Ø§Ù†ØªÙ‡Ø§Ø¡ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ© Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø£Ù† ÙŠØ³Ø¨Ù‚ ØªØ§Ø±ÙŠØ® Ø§Ù„ØªØµÙ†ÙŠØ¹ Ù„Ù„ØµÙ†Ù: %s'
                    % line.product_id.display_name
                )
            line._validate_tracking_batches(addition_qty)

    def action_approve_inspection(self):
        for receipt in self:
            if receipt.state != 'draft':
                raise UserError('ÙŠÙ…ÙƒÙ† Ø§Ø¹ØªÙ…Ø§Ø¯ Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ Ø§Ù„Ù…Ø³ÙˆØ¯Ø© ÙÙ‚Ø·')
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
            raise ValidationError('Ø³Ø¨Ø¨ Ø§Ù„Ø±ÙØ¶ Ù…Ø·Ù„ÙˆØ¨')
        for receipt in self:
            if receipt.state != 'draft':
                raise UserError('ÙŠÙ…ÙƒÙ† Ø±ÙØ¶ Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ Ø§Ù„Ù…Ø³ÙˆØ¯Ø© ÙÙ‚Ø·')
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
            raise ValidationError('Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ù†ÙˆØ¹ Ø§Ø³ØªÙ„Ø§Ù… Ù…Ø®Ø²Ù†ÙŠ Ù…Ø¹Ø±Ù')
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
            raise ValidationError('Ù„Ø§ ÙŠÙˆØ¬Ø¯ Ù…ÙˆÙ‚Ø¹ Ù…ÙˆØ±Ø¯ Ù…Ø¹Ø±Ù Ù„Ø­Ø±ÙƒØ© Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù…')
        return source

    def _prepare_picking_quantities(self, picking):
        self.ensure_one()
        addition_lines = self.line_ids.filtered(
            lambda line: not float_is_zero(
                line._addition_qty(), precision_rounding=line.uom_id.rounding,
            )
        )
        for line in addition_lines:
            addition_qty = line._addition_qty()
            move = picking.move_ids.filtered(
                lambda candidate: candidate.product_id == line.product_id
            )[:1]
            if not move:
                raise ValidationError(
                    'ØªØ¹Ø°Ø± Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø­Ø±ÙƒØ© Ø§Ù„ØµÙ†Ù: %s'
                    % line.product_id.display_name
                )
            if line.product_id.tracking == 'none':
                move.quantity = addition_qty
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
                    expiry_date = batch.expiry_date or line.expiry_date
                    if expiry_date and 'expiration_date' in self.env['stock.lot']._fields:
                        lot_values['expiration_date'] = fields.Datetime.to_datetime(
                            '%s 23:59:59' % expiry_date
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
        """Validate the addition voucher and move quantity + bonus into stock once."""
        for receipt in self:
            self.env.cr.execute(
                'SELECT id FROM %s WHERE id = %%s FOR UPDATE' % receipt._table,
                [receipt.id],
            )
            receipt.invalidate_recordset()

            if receipt.state == 'done':
                if receipt.picking_id and receipt.picking_id.state == 'done':
                    continue
                raise UserError('Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ù…ÙƒØªÙ…Ù„ ÙˆÙ„ÙƒÙ† Ø­Ø±ÙƒØ© Ø§Ù„Ù…Ø®Ø²ÙˆÙ† ØºÙŠØ± Ù…ÙƒØªÙ…Ù„Ø©')

            if receipt.state not in ('draft', 'awaiting_addition'):
                raise UserError('Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø§Ø¹ØªÙ…Ø§Ø¯ Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ÙÙŠ Ø­Ø§Ù„ØªÙ‡ Ø§Ù„Ø­Ø§Ù„ÙŠØ©')

            receipt._validate_addition()
            addition_lines = receipt.line_ids.filtered(
                lambda line: not float_is_zero(
                    line._addition_qty(), precision_rounding=line.uom_id.rounding,
                )
            )
            if not addition_lines:
                raise ValidationError('Ù„Ø§ ØªÙˆØ¬Ø¯ ÙƒÙ…ÙŠØ§Øª Ù„Ø¥Ø¶Ø§ÙØªÙ‡Ø§ Ù„Ù„Ù…Ø®Ø²ÙˆÙ†')

            picking = receipt.picking_id.sudo()
            if not picking:
                picking_type = receipt._find_incoming_picking_type()
                source_location = receipt._supplier_location(picking_type)
                origin = (
                    receipt.supply_order_reference
                    or receipt.supply_request_reference
                    or receipt.priced_delivery_number
                    or receipt.purchase_order_id.name
                    or receipt.origin_reference
                    or receipt.addition_number
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
                        'product_uom_qty': line._addition_qty(),
                        'product_uom': line.uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': receipt.destination_location_id.id,
                    }) for line in addition_lines],
                })
                receipt.picking_id = picking.id

            if picking.state == 'cancel':
                raise UserError('Ø­Ø±ÙƒØ© Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù… Ù…Ù„ØºØ§Ø©')
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
                raise ValidationError('ØªØ¹Ø°Ø± Ø¥ÙƒÙ…Ø§Ù„ Ø­Ø±ÙƒØ© Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ù„Ù„Ù…Ø®Ø²ÙˆÙ†')

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
    _description = 'Main Warehouse Addition Line'
    _order = 'id'

    receipt_id = fields.Many2one(
        'saycare.main.warehouse.receipt', string='Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©', required=True,
        ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Ø§Ù„ØµÙ†Ù', required=True, ondelete='restrict',
    )
    uom_id = fields.Many2one(
        'uom.uom', string='Ø§Ù„ÙˆØ­Ø¯Ø©', related='product_id.uom_id',
        store=True, readonly=True,
    )

    # New receipt-line snapshot fields.
    commercial_name = fields.Char(string='Ø§Ù„Ø§Ø³Ù… Ø§Ù„ØªØ¬Ø§Ø±ÙŠ')
    gtin = fields.Char(string='GTIN', index=True)
    manufacturing_date = fields.Date(string='ØªØ§Ø±ÙŠØ® Ø§Ù„ØªØµÙ†ÙŠØ¹')
    expiry_date = fields.Date(string='ØªØ§Ø±ÙŠØ® Ø§Ù†ØªÙ‡Ø§Ø¡ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ©')
    quantity = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ©', digits='Product Unit of Measure', default=0,
    )
    bonus_qty = fields.Float(
        string='Ø§Ù„Ø¨ÙˆÙ†Øµ', digits='Product Unit of Measure', default=0,
    )
    product_code = fields.Char(string='ÙƒÙˆØ¯ Ø§Ù„ØµÙ†Ù')

    # Legacy quantity/inspection fields retained for existing records.
    requested_qty = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ø·Ù„ÙˆØ¨Ø©', digits='Product Unit of Measure', default=0,
    )
    received_qty = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„ÙˆØ§Ø±Ø¯Ø©', digits='Product Unit of Measure', required=True,
    )
    accepted_qty = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ù‚Ø¨ÙˆÙ„Ø©', digits='Product Unit of Measure', required=True,
    )
    rejected_qty = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ø±ÙÙˆØ¶Ø©', digits='Product Unit of Measure', default=0,
    )
    unit_price = fields.Float(string='Ø³Ø¹Ø± Ø§Ù„ÙˆØ­Ø¯Ø©', digits='Product Price', default=0)
    quality_status = fields.Selection([
        ('accepted', 'Ù…Ø·Ø§Ø¨Ù‚'),
        ('conditional', 'Ù…Ù‚Ø¨ÙˆÙ„ Ø¨Ù…Ù„Ø§Ø­Ø¸Ø§Øª'),
        ('rejected', 'Ù…Ø±ÙÙˆØ¶'),
    ], string='Ø­Ø§Ù„Ø© Ø§Ù„ÙØ­Øµ', default='accepted', required=True)
    storage_location_note = fields.Char(string='Ù…ÙˆÙ‚Ø¹ Ø§Ù„ØªØ®Ø²ÙŠÙ†')
    notes = fields.Char(string='Ù…Ù„Ø§Ø­Ø¸Ø§Øª')
    batch_ids = fields.One2many(
        'saycare.main.warehouse.receipt.batch', 'receipt_line_id',
        string='Ø§Ù„Ø¯ÙØ¹Ø§Øª', copy=True,
    )

    def _addition_qty(self):
        self.ensure_one()
        new_total = (self.quantity or 0.0) + (self.bonus_qty or 0.0)
        if not float_is_zero(new_total, precision_rounding=self.uom_id.rounding):
            return new_total
        # Existing historical records have no new quantity/bonus values.
        return self.accepted_qty or 0.0

    @api.constrains(
        'requested_qty', 'received_qty', 'accepted_qty',
        'rejected_qty', 'unit_price', 'quantity', 'bonus_qty',
    )
    def _check_quantities(self):
        for line in self:
            values = [
                line.requested_qty, line.received_qty, line.accepted_qty,
                line.rejected_qty, line.unit_price, line.quantity, line.bonus_qty,
            ]
            if any(value < 0 for value in values):
                raise ValidationError('Ø§Ù„ÙƒÙ…ÙŠØ§Øª ÙˆØ§Ù„Ø£Ø³Ø¹Ø§Ø± Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø£Ù† ØªÙƒÙˆÙ† Ø³Ø§Ù„Ø¨Ø©')
            if float_compare(
                line.accepted_qty + line.rejected_qty,
                line.received_qty,
                precision_rounding=line.uom_id.rounding,
            ) > 0:
                raise ValidationError('Ø§Ù„Ù…Ù‚Ø¨ÙˆÙ„ ÙˆØ§Ù„Ù…Ø±ÙÙˆØ¶ ÙŠØªØ¬Ø§ÙˆØ²Ø§Ù† Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„ÙˆØ§Ø±Ø¯Ø©')

    @api.constrains('manufacturing_date', 'expiry_date')
    def _check_dates(self):
        for line in self:
            if (
                line.manufacturing_date and line.expiry_date
                and line.expiry_date < line.manufacturing_date
            ):
                raise ValidationError('ØªØ§Ø±ÙŠØ® Ø§Ù†ØªÙ‡Ø§Ø¡ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ© Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø£Ù† ÙŠØ³Ø¨Ù‚ ØªØ§Ø±ÙŠØ® Ø§Ù„ØªØµÙ†ÙŠØ¹')

    @api.constrains('receipt_id', 'product_id')
    def _check_duplicate_product(self):
        for line in self:
            if not line.receipt_id or not line.product_id:
                continue
            duplicates = line.receipt_id.line_ids.filtered(
                lambda candidate: candidate.product_id == line.product_id
            )
            if len(duplicates) > 1:
                raise ValidationError('Ù„Ø§ ÙŠÙ…ÙƒÙ† ØªÙƒØ±Ø§Ø± Ù†ÙØ³ Ø§Ù„ØµÙ†Ù Ø¯Ø§Ø®Ù„ Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©')

    def _validate_tracking_batches(self, target_qty=None):
        self.ensure_one()
        if self.product_id.tracking == 'none':
            return
        quantity_to_track = self._addition_qty() if target_qty is None else target_qty
        if float_is_zero(
            quantity_to_track, precision_rounding=self.uom_id.rounding,
        ):
            return
        if not self.batch_ids:
            raise ValidationError(
                'Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ø¯ÙØ¹Ø© Ù…Ø·Ù„ÙˆØ¨Ø© Ù„Ù„ØµÙ†Ù Ø§Ù„Ù…ØªØªØ¨Ø¹: %s'
                % self.product_id.display_name
            )
        batch_total = sum(self.batch_ids.mapped('quantity'))
        if float_compare(
            batch_total, quantity_to_track,
            precision_rounding=self.uom_id.rounding,
        ) != 0:
            raise ValidationError(
                'Ø¥Ø¬Ù…Ø§Ù„ÙŠ ÙƒÙ…ÙŠØ§Øª Ø§Ù„Ø¯ÙØ¹Ø§Øª ÙŠØ¬Ø¨ Ø£Ù† ÙŠØ³Ø§ÙˆÙŠ Ø§Ù„ÙƒÙ…ÙŠØ© Ù…Ø¹ Ø§Ù„Ø¨ÙˆÙ†Øµ Ù„Ù„ØµÙ†Ù: %s'
                % self.product_id.display_name
            )
        if self.product_id.tracking == 'serial' and any(
            float_compare(
                batch.quantity, 1.0,
                precision_rounding=self.uom_id.rounding,
            ) != 0
            for batch in self.batch_ids
        ):
            raise ValidationError('ÙƒÙ„ Ø±Ù‚Ù… Ù…Ø³Ù„Ø³Ù„ ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† ÙƒÙ…ÙŠØªÙ‡ ÙˆØ§Ø­Ø¯Ø§Ù‹')


class SaycareMainWarehouseReceiptBatch(models.Model):
    _name = 'saycare.main.warehouse.receipt.batch'
    _description = 'Main Warehouse Receipt Batch'
    _order = 'id'

    receipt_line_id = fields.Many2one(
        'saycare.main.warehouse.receipt.line', string='Ø³Ø·Ø± Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù…',
        required=True, ondelete='cascade', index=True,
    )
    batch_number = fields.Char(
        string='Ø±Ù‚Ù… Ø§Ù„Ø¯ÙØ¹Ø© / Ø§Ù„Ù…Ø³Ù„Ø³Ù„', required=True, index=True,
    )
    lot_number = fields.Char(string='Ø±Ù‚Ù… Ø§Ù„ØªØ´ØºÙŠÙ„Ø©')
    manufacturing_date = fields.Date(string='ØªØ§Ø±ÙŠØ® Ø§Ù„Ø¥Ù†ØªØ§Ø¬')
    expiry_date = fields.Date(string='ØªØ§Ø±ÙŠØ® Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ©')
    quantity = fields.Float(
        string='Ø§Ù„ÙƒÙ…ÙŠØ©', required=True, digits='Product Unit of Measure',
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for batch in self:
            if batch.quantity <= 0:
                raise ValidationError('ÙƒÙ…ÙŠØ© Ø§Ù„Ø¯ÙØ¹Ø© ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† Ø£ÙƒØ¨Ø± Ù…Ù† ØµÙØ±')
class MainWarehouseReceiptStatementTypeGuard(models.Model):
    _inherit = 'saycare.main.warehouse.receipt'

    _ALLOWED_STATEMENT_TYPES = {
        'توريد عادي',
        'هيئة شراء موحد',
        'على سبيل الامانة',
        'توريد مباشر',
    }

    @api.constrains('statement_type')
    def _validate_statement_type(self):
        for record in self:
            if (
                record.statement_type
                and record.statement_type not in self._ALLOWED_STATEMENT_TYPES
            ):
                raise ValidationError(
                    'نوع التوريد يجب أن يكون أحد القيم المعتمدة.'
                )
