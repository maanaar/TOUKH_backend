# -*- coding: utf-8 -*-
import json

from odoo import http
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


def _float_value(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s غير صالح' % field_name) from exc


def _current_employee(env):
    return env['hr.employee'].sudo().search([('user_id', '=', env.uid)], limit=1)


def _ensure_request_owner_or_admin(rec):
    employee = _current_employee(request.env)
    if request.env.user.has_group('base.group_system'):
        return
    if not employee or employee != rec.requester_employee_id:
        raise UserError('يمكن لطالب الاحتياج فقط تعديل الطلب أو إرساله')


def _ensure_warehouse_operator(rec):
    if request.env.user.has_group('base.group_system'):
        return
    if rec.directed_user_id and rec.directed_user_id != request.env.user:
        raise UserError('الطلب موجه إلى مستخدم آخر بالمخزن')


def _stock_qty(env, product_id, location_id):
    quants = env['stock.quant'].sudo().search([
        ('product_id', '=', product_id),
        ('location_id', 'child_of', location_id),
    ])
    return float(sum(quants.mapped(lambda quant: quant.quantity - quant.reserved_quantity)))


def _request_line_vals(env, raw, source_location_id):
    product_id = _int_value(
        raw.get('productId') or raw.get('product_id'),
        'الصنف',
    )
    product = env['product.product'].sudo().browse(product_id)
    if not product.exists() or not product.active:
        raise ValidationError('الصنف المختار غير موجود أو غير فعال')

    quant_exists = env['stock.quant'].sudo().search_count([
        ('product_id', '=', product.id),
        ('location_id', 'child_of', source_location_id),
    ])
    if not quant_exists:
        raise ValidationError('الصنف غير تابع للمخزن المصدر: %s' % product.display_name)

    qty = _float_value(
        raw.get('requestedQty', raw.get('requested_qty')),
        'الكمية المطلوبة',
    )
    if qty <= 0:
        raise ValidationError('الكمية المطلوبة يجب أن تكون أكبر من صفر')

    return {
        'product_id': product.id,
        'requested_qty': qty,
        'available_qty_snapshot': _stock_qty(env, product.id, source_location_id),
        'note': raw.get('note') or '',
    }


def _request_dict(rec):
    return {
        'id': rec.id,
        'name': rec.name,
        'requestDate': str(rec.request_date) if rec.request_date else None,
        'requiredDate': str(rec.required_date) if rec.required_date else None,
        'requesterEmployeeId': rec.requester_employee_id.id if rec.requester_employee_id else None,
        'requesterEmployeeName': rec.requester_employee_id.name if rec.requester_employee_id else '',
        'departmentId': rec.department_id.id if rec.department_id else None,
        'departmentName': rec.department_id.name if rec.department_id else '',
        'sourceWarehouseId': rec.source_warehouse_id.id if rec.source_warehouse_id else None,
        'sourceWarehouseName': rec.source_warehouse_id.name if rec.source_warehouse_id else '',
        'sourceLocationId': rec.source_location_id.id if rec.source_location_id else None,
        'sourceLocationName': rec.source_location_id.complete_name if rec.source_location_id else '',
        'destinationLocationId': rec.destination_location_id.id if rec.destination_location_id else None,
        'destinationLocationName': rec.destination_location_id.complete_name if rec.destination_location_id else '',
        'directedUserId': rec.directed_user_id.id if rec.directed_user_id else None,
        'directedUserName': rec.directed_user_id.name if rec.directed_user_id else '',
        'priority': rec.priority,
        'notes': rec.notes or '',
        'state': rec.state,
        'itemCount': rec.item_count,
        'requestedQtyTotal': rec.requested_qty_total,
        'issuedQtyTotal': rec.issued_qty_total,
        'submittedByName': rec.submitted_by_id.name if rec.submitted_by_id else '',
        'submittedAt': str(rec.submitted_at) if rec.submitted_at else None,
        'rejectionReason': rec.rejection_reason or '',
        'lines': [{
            'id': line.id,
            'productId': line.product_id.id,
            'productTemplateId': line.product_id.product_tmpl_id.id,
            'productName': line.product_id.display_name,
            'uomId': line.uom_id.id if line.uom_id else None,
            'uomName': line.uom_id.name if line.uom_id else '',
            'requestedQty': line.requested_qty,
            'availableQtySnapshot': line.available_qty_snapshot,
            'issuedQty': line.issued_qty,
            'remainingQty': line.remaining_qty,
            'note': line.note or '',
        } for line in rec.line_ids],
        'issues': [
            _issue_dict(issue, include_request=False)
            for issue in rec.issue_ids.sorted('id', reverse=True)
        ],
    }


def _issue_dict(rec, include_request=True):
    result = {
        'id': rec.id,
        'name': rec.name,
        'requestId': rec.request_id.id if rec.request_id else None,
        'requestName': rec.request_id.name if rec.request_id else '',
        'directIssue': rec.direct_issue,
        'issueDate': str(rec.issue_date) if rec.issue_date else None,
        'departmentId': rec.department_id.id if rec.department_id else None,
        'departmentName': rec.department_id.name if rec.department_id else '',
        'sourceWarehouseId': rec.source_warehouse_id.id if rec.source_warehouse_id else None,
        'sourceWarehouseName': rec.source_warehouse_id.name if rec.source_warehouse_id else '',
        'sourceLocationId': rec.source_location_id.id if rec.source_location_id else None,
        'sourceLocationName': rec.source_location_id.complete_name if rec.source_location_id else '',
        'destinationLocationId': rec.destination_location_id.id if rec.destination_location_id else None,
        'destinationLocationName': rec.destination_location_id.complete_name if rec.destination_location_id else '',
        'recipientEmployeeId': rec.recipient_employee_id.id if rec.recipient_employee_id else None,
        'recipientEmployeeName': rec.recipient_employee_id.name if rec.recipient_employee_id else '',
        'notes': rec.notes or '',
        'state': rec.state,
        'pickingId': rec.picking_id.id if rec.picking_id else None,
        'pickingName': rec.picking_id.name if rec.picking_id else '',
        'pickingState': rec.picking_id.state if rec.picking_id else '',
        'preparedByName': rec.prepared_by_id.name if rec.prepared_by_id else '',
        'preparedAt': str(rec.prepared_at) if rec.prepared_at else None,
        'receivedByName': rec.received_by_id.name if rec.received_by_id else '',
        'receivedAt': str(rec.received_at) if rec.received_at else None,
        'lines': [{
            'id': line.id,
            'requestLineId': line.request_line_id.id if line.request_line_id else None,
            'productId': line.product_id.id,
            'productTemplateId': line.product_id.product_tmpl_id.id,
            'productName': line.product_id.display_name,
            'uomId': line.uom_id.id if line.uom_id else None,
            'uomName': line.uom_id.name if line.uom_id else '',
            'requestedQtySnapshot': line.requested_qty_snapshot,
            'availableQtySnapshot': line.available_qty_snapshot,
            'issuedQty': line.issued_qty,
            'note': line.note or '',
        } for line in rec.line_ids],
    }
    if include_request and rec.request_id:
        result['request'] = {
            'id': rec.request_id.id,
            'name': rec.request_id.name,
            'state': rec.request_id.state,
        }
    return result


class DepartmentStockController(http.Controller):

    @http.route(
        '/api/v1/department-stock/master-data',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def master_data(self, **kw):
        env = request.env
        employee = _current_employee(env)
        warehouses = env['stock.warehouse'].sudo().search([])
        departments = env['hr.department'].sudo().search([])
        employees = env['hr.employee'].sudo().search([('active', '=', True)])
        users = env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)])

        return _json({
            'currentEmployee': {
                'id': employee.id if employee else None,
                'name': employee.name if employee else env.user.name,
                'departmentId': employee.department_id.id if employee and employee.department_id else None,
                'departmentName': employee.department_id.name if employee and employee.department_id else '',
                'isSystemAdmin': env.user.has_group('base.group_system'),
            },
            'warehouses': [{
                'id': warehouse.id,
                'name': warehouse.name,
                'code': warehouse.code or '',
                'locationId': warehouse.lot_stock_id.id if warehouse.lot_stock_id else None,
                'locationName': warehouse.lot_stock_id.complete_name if warehouse.lot_stock_id else '',
            } for warehouse in warehouses if warehouse.lot_stock_id],
            'departments': [{
                'id': department.id,
                'name': department.name,
                'locationId': department.department_location_id.id if department.department_location_id else None,
                'locationName': (
                    department.department_location_id.complete_name
                    if department.department_location_id else ''
                ),
                'hasValidLocation': bool(
                    department.department_location_id
                    and department.department_location_id.active
                    and department.department_location_id.usage == 'internal'
                ),
            } for department in departments],
            'employees': [{
                'id': employee_rec.id,
                'name': employee_rec.name,
                'departmentId': employee_rec.department_id.id if employee_rec.department_id else None,
                'departmentName': employee_rec.department_id.name if employee_rec.department_id else '',
                'userId': employee_rec.user_id.id if employee_rec.user_id else None,
            } for employee_rec in employees],
            'users': [{'id': user.id, 'name': user.name} for user in users],
        })

    @http.route(
        '/api/v1/department-stock-requests',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def list_requests(self, **kw):
        domain = []
        if kw.get('state'):
            domain.append(('state', '=', kw['state']))
        if kw.get('department_id'):
            domain.append(('department_id', '=', _int_value(kw['department_id'], 'القسم')))
        records = request.env['saycare.department.stock.request'].sudo().search(
            domain, order='id desc',
        )
        return _json([_request_dict(rec) for rec in records])

    @http.route(
        '/api/v1/department-stock-requests/<int:rec_id>',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def get_request(self, rec_id, **kw):
        rec = request.env['saycare.department.stock.request'].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'طلب الاحتياج غير موجود'}, 404)
        return _json(_request_dict(rec))

    @http.route(
        '/api/v1/department-stock-requests',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def create_request(self, **kw):
        try:
            body = _body()
            env = request.env
            auth_employee = _current_employee(env)
            is_admin = env.user.has_group('base.group_system')
            if not auth_employee and not is_admin:
                raise UserError('يجب ربط المستخدم بموظف لإنشاء طلب احتياج')

            requester_id = (
                auth_employee.id
                if auth_employee
                else _int_value(body.get('requesterEmployeeId'), 'طالب الاحتياج')
            )
            department_id = (
                auth_employee.department_id.id
                if auth_employee and auth_employee.department_id
                else _int_value(body.get('departmentId'), 'القسم الطالب')
            )
            warehouse_id = _int_value(body.get('sourceWarehouseId'), 'المخزن المصدر')

            warehouse = env['stock.warehouse'].sudo().browse(warehouse_id)
            if not warehouse.exists() or not warehouse.lot_stock_id:
                raise ValidationError('المخزن المختار غير صالح')

            lines = body.get('lines') or []
            if not lines:
                raise ValidationError('أضف صنفاً واحداً على الأقل')

            vals = {
                'requester_employee_id': requester_id,
                'department_id': department_id,
                'source_warehouse_id': warehouse.id,
                'directed_user_id': _int_value(
                    body.get('directedUserId'), 'موجه إلى', required=False,
                ),
                'priority': body.get('priority') or 'normal',
                'notes': body.get('notes') or '',
                'line_ids': [
                    (0, 0, _request_line_vals(env, line, warehouse.lot_stock_id.id))
                    for line in lines
                ],
            }
            if body.get('requestDate'):
                vals['request_date'] = body['requestDate']
            if body.get('requiredDate'):
                vals['required_date'] = body['requiredDate']

            with env.cr.savepoint():
                rec = env['saycare.department.stock.request'].sudo().create(vals)
                if body.get('submit'):
                    rec.action_submit()
            return _json(_request_dict(rec), 201)
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-requests/<int:rec_id>',
        type='http', auth='user', methods=['PUT'], csrf=False,
    )
    def update_request(self, rec_id, **kw):
        try:
            rec = request.env['saycare.department.stock.request'].sudo().browse(rec_id)
            if not rec.exists():
                return _json({'error': 'طلب الاحتياج غير موجود'}, 404)
            if rec.state != 'draft':
                raise UserError('يمكن تعديل الطلبات المسودة فقط')
            _ensure_request_owner_or_admin(rec)

            body = _body()
            vals = {}
            mapping = {
                'requestDate': 'request_date',
                'requiredDate': 'required_date',
                'sourceWarehouseId': 'source_warehouse_id',
                'directedUserId': 'directed_user_id',
                'priority': 'priority',
                'notes': 'notes',
            }
            for source, target in mapping.items():
                if source in body:
                    vals[target] = body[source] or False

            warehouse_id = _int_value(
                body.get('sourceWarehouseId') or rec.source_warehouse_id.id,
                'المخزن المصدر',
            )
            warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id)
            if not warehouse.exists() or not warehouse.lot_stock_id:
                raise ValidationError('المخزن المختار غير صالح')

            if 'lines' in body:
                lines = body.get('lines') or []
                if not lines:
                    raise ValidationError('أضف صنفاً واحداً على الأقل')
                vals['line_ids'] = [(5, 0, 0)] + [
                    (0, 0, _request_line_vals(
                        request.env, line, warehouse.lot_stock_id.id,
                    ))
                    for line in lines
                ]

            with request.env.cr.savepoint():
                rec.write(vals)
            return _json(_request_dict(rec))
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-requests/<int:rec_id>/submit',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def submit_request(self, rec_id, **kw):
        try:
            rec = request.env['saycare.department.stock.request'].sudo().browse(rec_id)
            if not rec.exists():
                return _json({'error': 'طلب الاحتياج غير موجود'}, 404)
            _ensure_request_owner_or_admin(rec)
            with request.env.cr.savepoint():
                rec.action_submit()
            return _json(_request_dict(rec))
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-requests/<int:rec_id>/reject',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def reject_request(self, rec_id, **kw):
        try:
            rec = request.env['saycare.department.stock.request'].sudo().browse(rec_id)
            if not rec.exists():
                return _json({'error': 'طلب الاحتياج غير موجود'}, 404)
            _ensure_warehouse_operator(rec)
            with request.env.cr.savepoint():
                rec.action_reject(_body().get('reason'))
            return _json(_request_dict(rec))
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-requests/<int:rec_id>/prepare-issue',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def prepare_request_issue(self, rec_id, **kw):
        try:
            env = request.env
            rec = env['saycare.department.stock.request'].sudo().browse(rec_id)
            if not rec.exists():
                return _json({'error': 'طلب الاحتياج غير موجود'}, 404)

            _ensure_warehouse_operator(rec)
            body = _body()
            raw_lines = body.get('lines') or []
            if not raw_lines:
                raise ValidationError('حدد كمية صرف لصنف واحد على الأقل')

            issue_lines = []
            for raw in raw_lines:
                request_line_id = _int_value(raw.get('requestLineId'), 'سطر الطلب')
                request_line = rec.line_ids.filtered(
                    lambda line: line.id == request_line_id
                )[:1]
                if not request_line:
                    raise ValidationError('أحد أسطر الطلب غير صالح')
                qty = _float_value(raw.get('issuedQty'), 'الكمية المصروفة')
                if qty <= 0:
                    continue
                issue_lines.append((0, 0, {
                    'request_line_id': request_line.id,
                    'product_id': request_line.product_id.id,
                    'requested_qty_snapshot': request_line.remaining_qty,
                    'issued_qty': qty,
                    'note': raw.get('note') or '',
                }))

            if not issue_lines:
                raise ValidationError('حدد كمية صرف لصنف واحد على الأقل')

            vals = {
                'request_id': rec.id,
                'recipient_employee_id': _int_value(
                    body.get('recipientEmployeeId'), 'مستلم القسم',
                ),
                'notes': body.get('notes') or '',
                'line_ids': issue_lines,
            }
            if body.get('issueDate'):
                vals['issue_date'] = body['issueDate']

            with env.cr.savepoint():
                issue = env['saycare.department.stock.issue'].sudo().create(vals)
                issue.action_prepare()
            return _json(_issue_dict(issue), 201)
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-issues',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def list_issues(self, **kw):
        records = request.env['saycare.department.stock.issue'].sudo().search([], order='id desc')
        return _json([_issue_dict(rec) for rec in records])

    @http.route(
        '/api/v1/department-stock-issues/<int:rec_id>',
        type='http', auth='user', methods=['GET'], csrf=False,
    )
    def get_issue(self, rec_id, **kw):
        rec = request.env['saycare.department.stock.issue'].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'إذن الصرف غير موجود'}, 404)
        return _json(_issue_dict(rec))

    @http.route(
        '/api/v1/department-stock-issues/direct',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def create_direct_issue(self, **kw):
        try:
            body = _body()
            env = request.env
            warehouse = env['stock.warehouse'].sudo().browse(
                _int_value(body.get('sourceWarehouseId'), 'المخزن المصدر')
            )
            department = env['hr.department'].sudo().browse(
                _int_value(body.get('departmentId'), 'القسم المستلم')
            )
            if not warehouse.exists() or not warehouse.lot_stock_id or not department.exists():
                raise ValidationError('المخزن أو القسم غير صالح')

            line_vals = []
            for raw in body.get('lines') or []:
                product = env['product.product'].sudo().browse(
                    _int_value(raw.get('productId'), 'الصنف')
                )
                if not product.exists() or not product.active:
                    raise ValidationError('الصنف المختار غير موجود أو غير فعال')
                quant_exists = env['stock.quant'].sudo().search_count([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', warehouse.lot_stock_id.id),
                ])
                if not quant_exists:
                    raise ValidationError(
                        'الصنف غير تابع للمخزن المصدر: %s' % product.display_name
                    )
                qty = _float_value(raw.get('issuedQty'), 'الكمية المصروفة')
                if qty <= 0:
                    continue
                line_vals.append((0, 0, {
                    'product_id': product.id,
                    'requested_qty_snapshot': qty,
                    'issued_qty': qty,
                    'note': raw.get('note') or '',
                }))

            if not line_vals:
                raise ValidationError('أضف صنفاً واحداً على الأقل')
            if not (body.get('notes') or '').strip():
                raise ValidationError('سبب الصرف المباشر مطلوب')

            vals = {
                'direct_issue': True,
                'department_id': department.id,
                'source_warehouse_id': warehouse.id,
                'recipient_employee_id': _int_value(
                    body.get('recipientEmployeeId'), 'مستلم القسم',
                ),
                'notes': body.get('notes') or '',
                'line_ids': line_vals,
            }
            if body.get('issueDate'):
                vals['issue_date'] = body['issueDate']

            with env.cr.savepoint():
                issue = env['saycare.department.stock.issue'].sudo().create(vals)
                issue.action_prepare()
            return _json(_issue_dict(issue), 201)
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)

    @http.route(
        '/api/v1/department-stock-issues/<int:rec_id>/receive',
        type='http', auth='user', methods=['POST'], csrf=False,
    )
    def receive_issue(self, rec_id, **kw):
        try:
            rec = request.env['saycare.department.stock.issue'].sudo().browse(rec_id)
            if not rec.exists():
                return _json({'error': 'إذن الصرف غير موجود'}, 404)
            with request.env.cr.savepoint():
                rec.action_receive()
            return _json(_issue_dict(rec))
        except (ValidationError, UserError) as exc:
            return _json({'error': str(exc)}, 400)
        except Exception as exc:
            return _json({'error': str(exc)}, 500)
