# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response


def http_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False, default=str)
    return Response(body, status=status, mimetype='application/json')


# ─────────────────────────────────────────────────────────────────────────────
#  hr.employee
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeController(http.Controller):

    @http.route('/api/v1/hr/employees', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.employee'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            data.append({
                'id':              rec.id,
                'name':            rec.name,
                'job_title':       rec.job_title or '',
                'job_id':          rec.job_id.id if rec.job_id else None,
                'job_name':        rec.job_id.name if rec.job_id else None,
                'department_id':   rec.department_id.id if rec.department_id else None,
                'department_name': rec.department_id.name if rec.department_id else None,
                'parent_id':       rec.parent_id.id if rec.parent_id else None,
                'parent_name':     rec.parent_id.name if rec.parent_id else None,
                'work_email':      rec.work_email or '',
                'work_phone':      rec.work_phone or '',
                'user_id':         rec.user_id.id if rec.user_id else None,
                'user_name':       rec.user_id.name if rec.user_id else None,
                'company_id':      rec.company_id.id if rec.company_id else None,
                'company_name':    rec.company_id.name if rec.company_id else None,
                'image_url':       '/web/image/hr.employee/%d/image_1920' % rec.id if rec.image_1920 else '',
            })
        return http_response(data)

    @http.route('/api/v1/hr/employees', type='http', auth='user', methods=['POST'], csrf=False)
    def create_one(self, **kw):
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)

        name = (body.get('name') or '').strip()
        if not name:
            return http_response({'error': 'name is required'}, 400)

        vals = {'name': name}
        if body.get('job_id'):
            vals['job_id'] = int(body['job_id'])
        if body.get('job_title'):
            vals['job_title'] = str(body['job_title'])
        if body.get('department_id'):
            vals['department_id'] = int(body['department_id'])
        if body.get('work_email'):
            vals['work_email'] = str(body['work_email'])
        if body.get('work_phone'):
            vals['work_phone'] = str(body['work_phone'])

        rec = request.env['hr.employee'].sudo().create(vals)
        return http_response({
            'id':              rec.id,
            'name':            rec.name,
            'job_title':       rec.job_title or '',
            'job_id':          rec.job_id.id if rec.job_id else None,
            'job_name':        rec.job_id.name if rec.job_id else None,
            'department_id':   rec.department_id.id if rec.department_id else None,
            'department_name': rec.department_id.name if rec.department_id else None,
            'work_email':      rec.work_email or '',
            'work_phone':      rec.work_phone or '',
            'active':          True,
        })


# ─────────────────────────────────────────────────────────────────────────────
#  hr.department
# ─────────────────────────────────────────────────────────────────────────────

class DepartmentController(http.Controller):

    @http.route('/api/v1/departments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.department'].sudo().search([('active', '=', True)])
        data = []
        for rec in records:
            data.append({
                'id':            rec.id,
                'name':          rec.name,
                'complete_name': rec.complete_name,
                'parent_id':     rec.parent_id.id if rec.parent_id else None,
                'parent_name':   rec.parent_id.name if rec.parent_id else None,
                'manager_id':    rec.manager_id.id if rec.manager_id else None,
                'manager_name':  rec.manager_id.name if rec.manager_id else None,
                'member_ids':    rec.member_ids.ids,
                'child_ids':     rec.child_ids.ids,
                'company_id':    rec.company_id.id if rec.company_id else None,
                'company_name':  rec.company_id.name if rec.company_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/departments', type='http', auth='user', methods=['POST'], csrf=False)
    def create_one(self, **kw):
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)
        name = (body.get('name') or '').strip()
        if not name:
            return http_response({'error': 'name is required'}, 400)
        rec = request.env['hr.department'].sudo().create({'name': name})
        return http_response({'id': rec.id, 'name': rec.name, 'complete_name': rec.complete_name})


# ─────────────────────────────────────────────────────────────────────────────
#  hr.job  — job positions
# ─────────────────────────────────────────────────────────────────────────────

class JobPositionController(http.Controller):

    @http.route('/api/v1/hr/jobs', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env['hr.job'].sudo().search([])
        data = []
        for rec in records:
            data.append({
                'id':              rec.id,
                'name':            rec.name,
                'department_id':   rec.department_id.id if rec.department_id else None,
                'department_name': rec.department_id.name if rec.department_id else None,
            })
        return http_response(data)

    @http.route('/api/v1/hr/jobs', type='http', auth='user', methods=['POST'], csrf=False)
    def create_one(self, **kw):
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)
        name = (body.get('name') or '').strip()
        if not name:
            return http_response({'error': 'name is required'}, 400)
        vals = {'name': name}
        if body.get('department_id'):
            vals['department_id'] = int(body['department_id'])
        rec = request.env['hr.job'].sudo().create(vals)
        return http_response({
            'id':              rec.id,
            'name':            rec.name,
            'department_id':   rec.department_id.id if rec.department_id else None,
            'department_name': rec.department_id.name if rec.department_id else None,
        })
