# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_document_ids = fields.Many2many(
        'ir.attachment', 'purchase_order_request_doc_rel', 'order_id', 'attachment_id',
        string='مستند طلب شراء')
    inspection_document_ids = fields.Many2many(
        'ir.attachment', 'purchase_order_inspection_doc_rel', 'order_id', 'attachment_id',
        string='مسند الفحص و الايضافة')
