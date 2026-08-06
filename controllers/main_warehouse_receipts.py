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
        raise ValidationError('بيانات الطلب غير صالحة') from exc
    if not isinstance(value, dict):
        raise ValidationError('بيانات الطلب يجب أن تكون كائناً')
    return value


def _int_value(value, field_name, required=True):
    if value in (None, '', False):
        if required:
            raise ValidationError('%s مطلوب' % field_name)
        return False
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s غير صالح' % field_name) from exc
    if required and result <= 0:
        raise ValidationError('%s غير صالح' % field_name)
    return result or False


def _float_value(value, field_name, default=0.0):
    if value in (None, ''):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s غير صالح' % field_name) from exc
    if result < 0:
        raise ValidationError('%s لا يمكن أن يكون سالباً' % field_name)
    return result


def _date_value(value, field_name, required=False):
    if value in (None, '', False):
        if required:
            raise ValidationError('%s مطلوب' % field_name)
        return False
    try:
        return fields.Date.to_date(value)
    except Exception as exc:
        raise ValidationError('%s غير صالح' % field_name) from exc


def _many2one(record):
    return record.id if record else None


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
        'productCode': line.product_id.default_code or '',
        'tracking': line.product_id.tracking or 'none',
        'uomId': line.uom_id.id,
        'uomName': line.uom_id.name,
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
        'sourceType': receipt.source_type,
        'purchaseOrderId': _many2one(receipt.purchase_order_id),
        'purchaseOrderName': receipt.purchase_order_id.name if receipt.purchase_order_id else '',
        'originReference': receipt.origin_reference or '',
        'supplierId': _many2one(receipt.supplier_id),
        'supplierName': receipt.supplier_id.display_name if receipt.supplier_id else '',
        'sourceDescription': receipt.source_description or '',
        'supplierInvoiceNumber': receipt.supplier_invoice_number or '',
        'supplierInvoiceDate': str(receipt.supplier_invoice_date) if receipt.supplier_invoice_date else None,
        'receiptDate': str(receipt.receipt_date) if receipt.receipt_date else None,
        'receiverEmployeeId': _many2one(receipt.receiver_employee_id),
        'receiverEmployeeName': receipt.receiver_employee_id.name if receipt.receiver_employee_id else '',
        'destinationLocationId': _many2one(receipt.destination_location_id),
        'destinationLocationName': receipt.destination_location_id.complete_name if receipt.destination_location_id else '',
        'supplyType': receipt.supply_type,
        'notes': receipt.notes or '',
        'itemCount': receipt.item_count,
        'requestedQtyTotal': receipt.requested_qty_total,
        'receivedQtyTotal': receipt.received_qty_total,
        'acceptedQtyTotal': receipt.accepted_qty_total,
        'rejectedQtyTotal': receipt.rejected_qty_total,
        'amountTotal': receipt.amount_total,
        'currencyId': _many2one(receipt.currency_id),
        'currencyName': receipt.currency_id.name if receipt.currency_id else '',
        'pickingId': _many2one(receipt.picking_id),
        'pickingName': receipt.picking_id.name if receipt.picking_id else '',
        'pickingState': receipt.picking_id.state if receipt.picking_id else '',
        'inspectionApprovedByName': receipt.inspection_approved_by_id.name if receipt.inspection_approved_by_id else '',
        'inspectionApprovedAt': str(receipt.inspection_approved_at) if receipt.inspection_approved_at else None,
        'additionApprovedByName': receipt.addition_approved_by_id.name if receipt.addition_approved_by_id else '',
        'additionApprovedAt': str(receipt.addition_approved_at) if receipt.addition_approved_at else None,
        'rejectionReason': receipt.rejection_reason or '',
        'createdAt': str(receipt.create_date) if receipt.create_date else None,
        'updatedAt': str(receipt.write_date) if receipt.write_date else None,
    }
    if include_lines:
        result['lines'] = [_line_data(line) for line in receipt.line_ids]
    return result


def _batch_commands(batches):
    commands = []
    for index, batch in enumerate(batches or [], start=1):
        if not isinstance(batch, dict):
            raise ValidationError('بيانات الدفعة رقم %s غير صالحة' % index)
        batch_number = (batch.get('batchNumber') or '').strip()
        if not batch_number:
            raise ValidationError('رقم الدفعة مطلوب')
        commands.append((0, 0, {
            'batch_number': batch_number,
            'lot_number': (batch.get('lotNumber') or '').strip(),
            'manufacturing_date': _date_value(batch.get('manufacturingDate'), 'تاريخ الإنتاج'),
            'expiry_date': _date_value(batch.get('expiryDate'), 'تاريخ الصلاحية'),
            'quantity': _float_value(batch.get('quantity'), 'كمية الدفعة'),
        }))
    return commands


def _line_commands(lines):
    if not isinstance(lines, list):
        raise ValidationError('قائمة الأصناف غير صالحة')
    commands = []
    for index, line in enumerate(lines, start=1):
        if not isinstance(line, dict):
            raise ValidationError('بيانات الصنف رقم %s غير صالحة' % index)
        product_id = _int_value(line.get('productId'), 'الصنف رقم %s' % index)
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            raise ValidationError('الصنف رقم %s غير موجود' % index)
        commands.append((0, 0, {
            'product_id': product.id,
            'requested_qty': _float_value(line.get('requestedQty'), 'الكمية المطلوبة'),
            'received_qty': _float_value(line.get('receivedQty'), 'الكمية الواردة'),
            'accepted_qty': _float_value(line.get('acceptedQty'), 'الكمية المقبولة'),
            'rejected_qty': _float_value(line.get('rejectedQty'), 'الكمية المرفوضة'),
            'unit_price': _float_value(line.get('unitPrice'), 'سعر الوحدة'),
            'quality_status': line.get('qualityStatus') or 'accepted',
            'storage_location_note': (line.get('storageLocationNote') or '').strip(),
            'notes': (line.get('notes') or '').strip(),
            'batch_ids': _batch_commands(line.get('batches')),
        }))
    return commands


def _receipt_values(body, replace_lines=False):
    values = {
        'source_type': body.get('sourceType') or 'purchase_order',
        'purchase_order_id': _int_value(body.get('purchaseOrderId'), 'أمر الشراء', required=False),
        'origin_reference': (body.get('originReference') or '').strip(),
        'supplier_id': _int_value(body.get('supplierId'), 'المورد', required=False),
        'source_description': (body.get('sourceDescription') or '').strip(),
        'supplier_invoice_number': (body.get('supplierInvoiceNumber') or '').strip(),
        'supplier_invoice_date': _date_value(body.get('supplierInvoiceDate'), 'تاريخ فاتورة المورد'),
        'receipt_date': _date_value(body.get('receiptDate'), 'تاريخ الاستلام', required=True),
        'receiver_employee_id': _int_value(body.get('receiverEmployeeId'), 'مستلم البضاعة'),
        'destination_location_id': _int_value(body.get('destinationLocationId'), 'المخزن المستلم'),
        'supply_type': body.get('supplyType') or 'normal',
        'notes': body.get('notes') or '',
    }

    if values['purchase_order_id']:
        purchase_order = request.env['purchase.order'].sudo().browse(values['purchase_order_id'])
        if not purchase_order.exists():
            raise ValidationError('أمر الشراء غير موجود')
        if not values['supplier_id']:
            values['supplier_id'] = purchase_order.partner_id.id
        if not values['origin_reference']:
            values['origin_reference'] = purchase_order.name

    if values['supplier_id']:
        supplier = request.env['res.partner'].sudo().browse(values['supplier_id'])
        if not supplier.exists():
            raise ValidationError('المورد غير موجود')

    receiver = request.env['hr.employee'].sudo().browse(values['receiver_employee_id'])
    if not receiver.exists():
        raise ValidationError('مستلم البضاعة غير موجود')

    destination = request.env['stock.location'].sudo().browse(values['destination_location_id'])
    if not destination.exists() or destination.usage != 'internal':
        raise ValidationError('المخزن المستلم غير صالح')

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
            stage = (query.get('stage') or '').strip()
            state = (query.get('state') or '').strip()
            search = (query.get('q') or '').strip()
            date_from = _date_value(query.get('date_from'), 'من تاريخ')
            date_to = _date_value(query.get('date_to'), 'إلى تاريخ')

            if stage == 'addition':
                domain.append(('state', 'in', ['awaiting_addition', 'done']))
            if state:
                domain.append(('state', '=', state))
            if date_from:
                domain.append(('receipt_date', '>=', date_from))
            if date_to:
                domain.append(('receipt_date', '<=', date_to))
            if search:
                domain.extend([
                    '|', '|', '|', '|', '|', '|',
                    ('name', 'ilike', search),
                    ('addition_number', 'ilike', search),
                    ('origin_reference', 'ilike', search),
                    ('supplier_invoice_number', 'ilike', search),
                    ('supplier_id.name', 'ilike', search),
                    ('destination_location_id.complete_name', 'ilike', search),
                    ('receiver_employee_id.name', 'ilike', search),
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
            return _json({'error': 'تعذر تحميل مستندات الاستلام'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>', type='http',
        auth='user', methods=['GET'], csrf=False,
    )
    def get_receipt(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'محضر الفحص غير موجود'}, 404)
        return _json(_receipt_data(receipt))

    @http.route(
        '/api/v1/main-warehouse-receipts', type='http', auth='user',
        methods=['POST'], csrf=False,
    )
    def create_receipt(self, **query):
        try:
            values = _receipt_values(_body())
            if not values.get('line_ids'):
                raise ValidationError('أضف صنفاً واحداً على الأقل')
            receipt = request.env['saycare.main.warehouse.receipt'].sudo().create(values)
            return _json(_receipt_data(receipt), 201)
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'تعذر إنشاء محضر الفحص'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>', type='http',
        auth='user', methods=['PUT'], csrf=False,
    )
    def update_receipt(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'محضر الفحص غير موجود'}, 404)
        try:
            receipt.write(_receipt_values(_body(), replace_lines=True))
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'تعذر تحديث محضر الفحص'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/approve-inspection',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def approve_inspection(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'محضر الفحص غير موجود'}, 404)
        try:
            receipt.action_approve_inspection()
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'تعذر اعتماد محضر الفحص'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/reject-inspection',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def reject_inspection(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'محضر الفحص غير موجود'}, 404)
        try:
            receipt.action_reject_inspection(_body().get('reason'))
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'تعذر رفض محضر الفحص'}, 500)

    @http.route(
        '/api/v1/main-warehouse-receipts/<int:receipt_id>/finalize-addition',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def finalize_addition(self, receipt_id, **query):
        receipt = request.env['saycare.main.warehouse.receipt'].sudo().browse(receipt_id)
        if not receipt.exists():
            return _json({'error': 'محضر الفحص غير موجود'}, 404)
        try:
            receipt.action_finalize_addition()
            return _json(_receipt_data(receipt))
        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            return _json({'error': str(exc)}, 400)
        except Exception:
            request.env.cr.rollback()
            return _json({'error': 'تعذر اعتماد إذن الإضافة'}, 500)
