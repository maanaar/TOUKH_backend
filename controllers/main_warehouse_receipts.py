# -*- coding: utf-8 -*-
import json

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import Response, request


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
    )


def _body():
    try:
        value = json.loads(request.httprequest.data or '{}')
    except Exception as exc:
        raise ValidationError('Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ø·Ù„Ø¨ ØºÙŠØ± ØµØ§Ù„Ø­Ø©') from exc
    if not isinstance(value, dict):
        raise ValidationError('Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ø·Ù„Ø¨ ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† ÙƒØ§Ø¦Ù†Ø§Ù‹')
    return value


def _int_value(value, field_name, required=True):
    if value in (None, '', False):
        if required:
            raise ValidationError('%s Ù…Ø·Ù„ÙˆØ¨' % field_name)
        return False
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s ØºÙŠØ± ØµØ§Ù„Ø­' % field_name) from exc
    if required and result <= 0:
        raise ValidationError('%s ØºÙŠØ± ØµØ§Ù„Ø­' % field_name)
    return result or False


def _float_value(value, field_name, default=0.0):
    if value in (None, ''):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s ØºÙŠØ± ØµØ§Ù„Ø­' % field_name) from exc
    if result < 0:
        raise ValidationError('%s Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø£Ù† ÙŠÙƒÙˆÙ† Ø³Ø§Ù„Ø¨Ø§Ù‹' % field_name)
    return result


def _date_value(value, field_name, required=False):
    if value in (None, '', False):
        if required:
            raise ValidationError('%s Ù…Ø·Ù„ÙˆØ¨' % field_name)
        return False
    try:
        return fields.Date.to_date(value)
    except Exception as exc:
        raise ValidationError('%s ØºÙŠØ± ØµØ§Ù„Ø­' % field_name) from exc


def _many2one(record):
    return record.id if record else None


def _attachment_data(attachment):
    return {
        'id': attachment.id,
        'name': attachment.name or '',
        'mimetype': attachment.mimetype or '',
        'fileSize': attachment.file_size or 0,
        'url': '/web/content/%s?download=true' % attachment.id,
    }


def _attachment_list(attachments):
    return [_attachment_data(attachment) for attachment in attachments]


def _batch_data(batch):
    return {
        'id': batch.id,
        'batchNumber': batch.batch_number or '',
        'lotNumber': batch.lot_number or '',
        'manufacturingDate': str(batch.manufacturing_date) if batch.manufacturing_date else None,
        'expiryDate': str(batch.expiry_date) if batch.expiry_date else None,
        'quantity': batch.quantity,
    }


def _line_data(line):
    return {
        'id': line.id,
        'productId': line.product_id.id,
        'productName': line.product_id.display_name,
        'commercialName': line.commercial_name or line.product_id.display_name,
        'productCode': line.product_code or line.product_id.default_code or '',
        'gtin': line.gtin or '',
        'manufacturingDate': str(line.manufacturing_date) if line.manufacturing_date else None,
        'expiryDate': str(line.expiry_date) if line.expiry_date else None,
        'quantity': line.quantity,
        'bonusQty': line.bonus_qty,
        'stockQty': line._addition_qty(),
        'tracking': line.product_id.tracking or 'none',
        'uomId': line.uom_id.id,
        'uomName': line.uom_id.name,
        # Legacy response fields retained during the frontend transition.
        'requestedQty': line.requested_qty,
        'receivedQty': line.received_qty,
        'acceptedQty': line.accepted_qty,
        'rejectedQty': line.rejected_qty,
        'unitPrice': line.unit_price,
        'lineTotal': line.accepted_qty * line.unit_price,
        'qualityStatus': line.quality_status,
        'storageLocationNote': line.storage_location_note or '',
        'notes': line.notes or '',
        'batches': [_batch_data(batch) for batch in line.batch_ids],
    }


def _receipt_data(receipt, include_lines=True):
    result = {
        'id': receipt.id,
        'name': receipt.name,
        'additionNumber': receipt.addition_number if receipt.addition_number != 'New' else '',
        'state': receipt.state,
        'pricedDeliveryNumber': receipt.priced_delivery_number or '',
        'supplierId': _many2one(receipt.supplier_id),
        'supplierName': receipt.supplier_id.display_name if receipt.supplier_id else '',
        'supplierNumber': receipt.supplier_number or '',
        'statementType': receipt.statement_type or '',
        'supplyRequestReference': receipt.supply_request_reference or '',
        'supplyOrderReference': receipt.supply_order_reference or '',
        'issueDate': str(receipt.issue_date) if receipt.issue_date else None,
        'inspectionAttachments': _attachment_list(receipt.inspection_attachment_ids),
        'destinationLocationId': _many2one(receipt.destination_location_id),
        'destinationLocationName': receipt.destination_location_id.complete_name if receipt.destination_location_id else '',
        'notes': receipt.notes or '',
        'itemCount': receipt.item_count,
        'stockQtyTotal': sum(receipt.line_ids.mapped(lambda line: line._addition_qty())),
        'pickingId': _many2one(receipt.picking_id),
        'pickingName': receipt.picking_id.name if receipt.picking_id else '',
        'pickingState': receipt.picking_id.state if receipt.picking_id else '',
        'additionApprovedByName': receipt.addition_approved_by_id.name if receipt.addition_approved_by_id else '',
        'additionApprovedAt': str(receipt.addition_approved_at) if receipt.addition_approved_at else None,
        'createdAt': str(receipt.create_date) if receipt.create_date else None,
        'updatedAt': str(receipt.write_date) if receipt.write_date else None,
        # Legacy fields retained so older clients/records remain readable.
        'sourceType': receipt.source_type,
        'purchaseOrderId': _many2one(receipt.purchase_order_id),
        'purchaseOrderName': receipt.purchase_order_id.name if receipt.purchase_order_id else '',
        'originReference': receipt.origin_reference or '',
        'sourceDescription': receipt.source_description or '',
        'supplierInvoiceNumber': receipt.supplier_invoice_number or '',
        'supplierInvoiceDate': str(receipt.supplier_invoice_date) if receipt.supplier_invoice_date else None,
        'receiptDate': str(receipt.receipt_date) if receipt.receipt_date else None,
        'receiverEmployeeId': _many2one(receipt.receiver_employee_id),
        'receiverEmployeeName': receipt.receiver_employee_id.name if receipt.receiver_employee_id else '',
        'supplyType': receipt.supply_type,
        'requestedQtyTotal': receipt.requested_qty_total,
        'receivedQtyTotal': receipt.received_qty_total,
        'acceptedQtyTotal': receipt.accepted_qty_total,
        'rejectedQtyTotal': receipt.rejected_qty_total,
        'amountTotal': receipt.amount_total,
        'currencyId': _many2one(receipt.currency_id),
        'currencyName': receipt.currency_id.name if receipt.currency_id else '',
        'inspectionApprovedByName': receipt.inspection_approved_by_id.name if receipt.inspection_approved_by_id else '',
        'inspectionApprovedAt': str(receipt.inspection_approved_at) if receipt.inspection_approved_at else None,
        'rejectionReason': receipt.rejection_reason or '',
    }
    if include_lines:
        result['lines'] = [_line_data(line) for line in receipt.line_ids]
    return result


def _batch_commands(batches):
    commands = []
    for index, batch in enumerate(batches or [], start=1):
        if not isinstance(batch, dict):
            raise ValidationError('Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ø¯ÙØ¹Ø© Ø±Ù‚Ù… %s ØºÙŠØ± ØµØ§Ù„Ø­Ø©' % index)
        batch_number = (batch.get('batchNumber') or '').strip()
        if not batch_number:
            raise ValidationError('Ø±Ù‚Ù… Ø§Ù„Ø¯ÙØ¹Ø© Ù…Ø·Ù„ÙˆØ¨')
        commands.append((0, 0, {
            'batch_number': batch_number,
            'lot_number': (batch.get('lotNumber') or '').strip(),
            'manufacturing_date': _date_value(batch.get('manufacturingDate'), 'ØªØ§Ø±ÙŠØ® Ø§Ù„Ø¥Ù†ØªØ§Ø¬'),
            'expiry_date': _date_value(batch.get('expiryDate'), 'ØªØ§Ø±ÙŠØ® Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ©'),
            'quantity': _float_value(batch.get('quantity'), 'ÙƒÙ…ÙŠØ© Ø§Ù„Ø¯ÙØ¹Ø©'),
        }))
    return commands


def _line_commands(lines):
    if not isinstance(lines, list):
        raise ValidationError('Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø£ØµÙ†Ø§Ù ØºÙŠØ± ØµØ§Ù„Ø­Ø©')

    commands = []
    for index, line in enumerate(lines, start=1):
        if not isinstance(line, dict):
            raise ValidationError('Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØµÙ†Ù Ø±Ù‚Ù… %s ØºÙŠØ± ØµØ§Ù„Ø­Ø©' % index)

        product_id = _int_value(line.get('productId'), 'Ø§Ù„ØµÙ†Ù Ø±Ù‚Ù… %s' % index)
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            raise ValidationError('Ø§Ù„ØµÙ†Ù Ø±Ù‚Ù… %s ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯' % index)

        uses_new_quantity_contract = 'quantity' in line or 'bonusQty' in line
        if uses_new_quantity_contract:
            quantity = _float_value(line.get('quantity'), 'Ø§Ù„ÙƒÙ…ÙŠØ©')
            bonus_qty = _float_value(line.get('bonusQty'), 'Ø§Ù„Ø¨ÙˆÙ†Øµ')
            stock_qty = quantity + bonus_qty
            requested_qty = quantity
            received_qty = stock_qty
            accepted_qty = stock_qty
            rejected_qty = 0.0
            quality_status = 'accepted'
        else:
            quantity = 0.0
            bonus_qty = 0.0
            requested_qty = _float_value(line.get('requestedQty'), 'Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ø·Ù„ÙˆØ¨Ø©')
            received_qty = _float_value(line.get('receivedQty'), 'Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„ÙˆØ§Ø±Ø¯Ø©')
            accepted_qty = _float_value(line.get('acceptedQty'), 'Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ù‚Ø¨ÙˆÙ„Ø©')
            rejected_qty = _float_value(line.get('rejectedQty'), 'Ø§Ù„ÙƒÙ…ÙŠØ© Ø§Ù„Ù…Ø±ÙÙˆØ¶Ø©')
            quality_status = line.get('qualityStatus') or 'accepted'

        commands.append((0, 0, {
            'product_id': product.id,
            'commercial_name': (line.get('commercialName') or product.display_name or '').strip(),
            'gtin': (line.get('gtin') or '').strip(),
            'manufacturing_date': _date_value(line.get('manufacturingDate'), 'ØªØ§Ø±ÙŠØ® Ø§Ù„ØªØµÙ†ÙŠØ¹'),
            'expiry_date': _date_value(line.get('expiryDate'), 'ØªØ§Ø±ÙŠØ® Ø§Ù†ØªÙ‡Ø§Ø¡ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ©'),
            'quantity': quantity,
            'bonus_qty': bonus_qty,
            'product_code': (line.get('productCode') or product.default_code or '').strip(),
            'requested_qty': requested_qty,
            'received_qty': received_qty,
            'accepted_qty': accepted_qty,
            'rejected_qty': rejected_qty,
            'unit_price': _float_value(line.get('unitPrice'), 'Ø³Ø¹Ø± Ø§Ù„ÙˆØ­Ø¯Ø©'),
            'quality_status': quality_status,
            'storage_location_note': (line.get('storageLocationNote') or '').strip(),
            'notes': (line.get('notes') or '').strip(),
            'batch_ids': _batch_commands(line.get('batches')),
        }))
    return commands


def _receipt_values(body, replace_lines=False):
    issue_date = _date_value(
        body.get('issueDate') or body.get('receiptDate'),
        'ØªØ§Ø±ÙŠØ® Ø¥ØµØ¯Ø§Ø± Ø§Ù„Ø¥Ø°Ù†', required=True,
    )
    receipt_date = _date_value(
        body.get('receiptDate') or body.get('issueDate'),
        'ØªØ§Ø±ÙŠØ® Ø§Ù„Ø§Ø³ØªÙ„Ø§Ù…', required=True,
    )

    values = {
        'priced_delivery_number': (body.get('pricedDeliveryNumber') or '').strip(),
        'supplier_id': _int_value(body.get('supplierId'), 'Ø§Ù„Ù…ÙˆØ±Ø¯', required=False),
        'supplier_number': (body.get('supplierNumber') or '').strip(),
        'statement_type': (body.get('statementType') or '').strip(),
        'supply_request_reference': (body.get('supplyRequestReference') or '').strip(),
        'supply_order_reference': (body.get('supplyOrderReference') or '').strip(),
        'issue_date': issue_date,
        'receipt_date': receipt_date,
        'destination_location_id': _int_value(body.get('destinationLocationId'), 'Ø§Ù„Ù…Ø®Ø²Ù† Ø§Ù„Ù…Ø³ØªÙ„Ù…'),
        'notes': body.get('notes') or '',
        # Legacy/default fields retained for compatibility.
        'source_type': body.get('sourceType') or 'purchase_order',
        'purchase_order_id': _int_value(body.get('purchaseOrderId'), 'Ø£Ù…Ø± Ø§Ù„Ø´Ø±Ø§Ø¡', required=False),
        'origin_reference': (body.get('originReference') or '').strip(),
        'source_description': (body.get('sourceDescription') or '').strip(),
        'supplier_invoice_number': (body.get('supplierInvoiceNumber') or '').strip(),
        'supplier_invoice_date': _date_value(body.get('supplierInvoiceDate'), 'ØªØ§Ø±ÙŠØ® ÙØ§ØªÙˆØ±Ø© Ø§Ù„Ù…ÙˆØ±Ø¯'),
        'receiver_employee_id': _int_value(body.get('receiverEmployeeId'), 'Ù…Ø³ØªÙ„Ù… Ø§Ù„Ø¨Ø¶Ø§Ø¹Ø©', required=False),
        'supply_type': body.get('supplyType') or 'normal',
    }

    if values['purchase_order_id']:
        purchase_order = request.env['purchase.order'].sudo().browse(values['purchase_order_id'])
        if not purchase_order.exists():
            raise ValidationError('Ø£Ù…Ø± Ø§Ù„Ø´Ø±Ø§Ø¡ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯')
        if not values['supplier_id']:
            values['supplier_id'] = purchase_order.partner_id.id
        if not values['origin_reference']:
            values['origin_reference'] = purchase_order.name

    if values['supplier_id']:
        supplier = request.env['res.partner'].sudo().browse(values['supplier_id'])
        if not supplier.exists():
            raise ValidationError('Ø§Ù„Ù…ÙˆØ±Ø¯ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯')
        if not values['supplier_number'] and supplier.ref:
            values['supplier_number'] = supplier.ref

    if values['receiver_employee_id']:
        receiver = request.env['hr.employee'].sudo().browse(values['receiver_employee_id'])
        if not receiver.exists():
            raise ValidationError('Ù…Ø³ØªÙ„Ù… Ø§Ù„Ø¨Ø¶Ø§Ø¹Ø© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯')

    destination = request.env['stock.location'].sudo().browse(values['destination_location_id'])
    if not destination.exists() or destination.usage != 'internal':
        raise ValidationError('Ø§Ù„Ù…Ø®Ø²Ù† Ø§Ù„Ù…Ø³ØªÙ„Ù… ØºÙŠØ± ØµØ§Ù„Ø­')

    if 'lines' in body:
        line_commands = _line_commands(body.get('lines'))
        values['line_ids'] = [(5, 0, 0)] + line_commands if replace_lines else line_commands
    return values


class MainWarehouseReceiptController(http.Controller):

    @http.route(
        '/api/v1/main-warehouse-receipts', type='http', auth='user',
        methods=['GET'], csrf=False,
    )
    def list_receipts(self, **query):
        try:
            domain = []
            state = (query.get('state') or '').strip()
            search = (query.get('q') or '').strip()
            date_from = _date_value(query.get('date_from'), 'Ù…Ù† ØªØ§Ø±ÙŠØ®')
            date_to = _date_value(query.get('date_to'), 'Ø¥Ù„Ù‰ ØªØ§Ø±ÙŠØ®')

            # stage remains accepted for backward compatibility, but the new
            # addition screen must also see drafts so there is no stage filter.
            if state:
                domain.append(('state', '=', state))
            if date_from:
                domain.append(('issue_date', '>=', date_from))
            if date_to:
                domain.append(('issue_date', '<=', date_to))
            if search:
                domain.extend([
                    '|', '|', '|', '|', '|', '|', '|', '|',
                    ('addition_number', 'ilike', search),
                    ('priced_delivery_number', 'ilike', search),
                    ('supplier_number', 'ilike', search),
                    ('statement_type', 'ilike', search),
                    ('supply_request_reference', 'ilike', search),
                    ('supply_order_reference', 'ilike', search),
                    ('supplier_id.name', 'ilike', search),
                    ('destination_location_id.complete_name', 'ilike', search),
                    ('name', 'ilike', search),
                ])

            records = request.env['saycare.main.warehouse.receipt'].sudo().search(
                domain, order='id desc'
            )
            return _json([_receipt_data(record, include_lines=False) for record in records])
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± ØªØ­Ù…ÙŠÙ„ Ø£Ø°ÙˆÙ† Ø§Ù„Ø¥Ø¶Ø§ÙØ©'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>', type='http',
        auth='user', methods=['GET'], csrf=False,
    )
    def get_receipt(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        return _json(_receipt_data(receipt))

    @http.route(
        '/api/v1/main-warehouse-receipts', type='http', auth='user',
        methods=['POST'], csrf=False,
    )
    def create_receipt(self, **query):
        try:
            values = _receipt_values(_body())
            if not values.get('line_ids'):
                raise ValidationError('Ø£Ø¶Ù ØµÙ†ÙØ§Ù‹ ÙˆØ§Ø­Ø¯Ø§Ù‹ Ø¹Ù„Ù‰ Ø§Ù„Ø£Ù‚Ù„')
            receipt = request.env['saycare.main.warehouse.receipt'].sudo().create(values)
            return _json(_receipt_data(receipt), 201)
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø¥Ù†Ø´Ø§Ø¡ Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>', type='http',
        auth='user', methods=['PUT'], csrf=False,
    )
    def update_receipt(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            receipt.write(_receipt_values(_body(), replace_lines=True))
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± ØªØ­Ø¯ÙŠØ« Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©'}, 500)

    # Legacy inspection actions remain available for old callers/records.
    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/approve-inspection',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def approve_inspection(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            receipt.action_approve_inspection()
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø§Ø¹ØªÙ…Ø§Ø¯ Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/reject-inspection',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def reject_inspection(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            receipt.action_reject_inspection(_body().get('reason'))
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø±ÙØ¶ Ù…Ø­Ø¶Ø± Ø§Ù„ÙØ­Øµ'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/finalize-addition',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def finalize_addition(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            receipt.action_finalize_addition()
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø§Ø¹ØªÙ…Ø§Ø¯ Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ©'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/inspection-attachments',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def add_inspection_attachment(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            body = _body()
            data = body.get('data')
            if not data:
                raise ValidationError('Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„Ù…Ø±ÙÙ‚ Ù…Ø·Ù„ÙˆØ¨Ø©')
            attachment = request.env['ir.attachment'].sudo().create({
                'name': body.get('name') or 'inspection-attachment',
                'datas': data,
                'mimetype': body.get('mimetype') or False,
                'res_model': 'saycare.main.warehouse.receipt',
                'res_id': receipt.id,
            })
            receipt.inspection_attachment_ids = [(4, attachment.id)]
            return _json(_attachment_list(receipt.inspection_attachment_ids), 201)
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø±ÙØ¹ Ù…Ø±ÙÙ‚ Ø§Ù„ÙØ­Øµ'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/inspection-attachments/<int:attachment_id>',
        type='http', auth='user', methods=['DELETE'], csrf=False,
    )
    def remove_inspection_attachment(self, receipt_id, attachment_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'Ø¥Ø°Ù† Ø§Ù„Ø¥Ø¶Ø§ÙØ© ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
        try:
            attachment = receipt.inspection_attachment_ids.filtered(
                lambda item: item.id == attachment_id
            )
            if not attachment:
                return _json({'error': 'Ø§Ù„Ù…Ø±ÙÙ‚ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}, 404)
            receipt.inspection_attachment_ids = [(3, attachment_id)]
            attachment.sudo().unlink()
            return _json(_attachment_list(receipt.inspection_attachment_ids))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'ØªØ¹Ø°Ø± Ø­Ø°Ù Ù…Ø±ÙÙ‚ Ø§Ù„ÙØ­Øµ'}, 500)
