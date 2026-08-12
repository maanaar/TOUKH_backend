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
                'user_login':      rec.user_id.login if rec.user_id else None,
                'user_active':     rec.user_id.active if rec.user_id else None,
                'medical_role':    rec.medical_role or '',
                'doctor_grade':    rec.doctor_grade or '',
                'specialty_id':    rec.specialty_id.id if rec.specialty_id else None,
                'specialty_name':  rec.specialty_id.name if rec.specialty_id else '',
                'nurse_specialty_ids':   rec.nurse_specialty_ids.ids,
                'nurse_specialty_names': [s.name for s in rec.nurse_specialty_ids],
                'company_id':      rec.company_id.id if rec.company_id else None,
                'company_name':    rec.company_id.name if rec.company_id else None,
                'image_url':       '/web/image/hr.employee/%d/image_1920' % rec.id if rec.image_1920 else '',
            })
        return http_response(data)

    @http.route('/api/v1/hr/current-employee', type='http', auth='user', methods=['GET'], csrf=False)
    def get_current(self, **kw):
        emp = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id), ('active', '=', True)], limit=1
        )
        if not emp:
            return http_response({'error': 'no employee linked to current user'}, 404)
        # Load access from ir.config_parameter (device-independent)
        param = request.env['ir.config_parameter'].sudo().get_param(
            f'his.emp_access.{emp.id}', default=''
        )
        try:
            access = json.loads(param) if param else None
        except Exception:
            access = None
        return http_response({
            'id':              emp.id,
            'name':            emp.name,
            'department_id':   emp.department_id.id if emp.department_id else None,
            'department_name': emp.department_id.name if emp.department_id else None,
            'job_title':       emp.job_title or '',
            'user_id':         emp.user_id.id if emp.user_id else None,
            'medical_role':    emp.medical_role or '',
            'nurse_specialty_ids':   emp.nurse_specialty_ids.ids,
            'nurse_specialty_names': [s.name for s in emp.nurse_specialty_ids],
            'access':          access,
        })

    @http.route('/api/v1/hr/employees/<int:employee_id>/access', type='http', auth='user', methods=['PUT'], csrf=False)
    def set_employee_access(self, employee_id, **kw):
        emp = request.env['hr.employee'].sudo().browse(employee_id)
        if not emp.exists():
            return http_response({'error': 'employee not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)
        access_json = json.dumps(body, ensure_ascii=False)
        request.env['ir.config_parameter'].sudo().set_param(
            f'his.emp_access.{employee_id}', access_json
        )
        return http_response({'ok': True})

    @http.route('/api/v1/hr/employees/<int:employee_id>/create-user', type='http', auth='user', methods=['POST'], csrf=False)
    def create_employee_user(self, employee_id, **kw):
        emp = request.env['hr.employee'].sudo().browse(employee_id)
        if not emp.exists():
            return http_response({'error': 'employee not found'}, 404)
        if emp.user_id:
            return http_response({
                'error': 'employee already has a user account',
                'user_id': emp.user_id.id,
                'user_login': emp.user_id.login,
            }, 409)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)
        email    = (body.get('email') or '').strip().lower()
        password = body.get('password', '')
        if not email:
            return http_response({'error': 'email is required'}, 400)
        if not password:
            return http_response({'error': 'password is required'}, 400)
        existing = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if existing:
            return http_response({'error': 'a user with this email already exists'}, 409)
        env  = request.env
        user = env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name':  emp.name,
            'login': email,
            'email': email,
        })
        user.sudo().write({'password': password})
        emp.sudo().write({'user_id': user.id})
        return http_response({
            'ok':          True,
            'user_id':     user.id,
            'user_login':  user.login,
            'user_name':   user.name,
            'user_active': user.active,
        }, 201)

    @http.route('/api/v1/hr/employees/<int:employee_id>/user', type='http', auth='user', methods=['PATCH'], csrf=False)
    def update_employee_user(self, employee_id, **kw):
        emp = request.env['hr.employee'].sudo().browse(employee_id)
        if not emp.exists() or not emp.user_id:
            return http_response({'error': 'employee or linked user not found'}, 404)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)

        target_user = emp.user_id
        caller      = request.env.user  # authenticated user making the request

        # Block password changes on Odoo admin (uid=2) or superuser (uid=1)
        if body.get('password') and target_user.id in (1, 2):
            return http_response({'error': 'لا يمكن تغيير كلمة مرور حساب النظام من هنا'}, 403)

        # Block a non-admin caller from changing another user's password
        caller_is_admin = caller._is_admin()
        if body.get('password') and not caller_is_admin:
            return http_response({'error': 'غير مصرح'}, 403)

        # Block deactivating a higher-privileged account
        if 'active' in body and not bool(body['active']):
            if target_user.id in (1, 2) or (target_user._is_admin() and not caller_is_admin):
                return http_response({'error': 'لا يمكن تعطيل هذا الحساب'}, 403)

        user = target_user.sudo()
        if body.get('password'):
            user.write({'password': body['password']})
        if 'active' in body:
            user.write({'active': bool(body['active'])})
        return http_response({
            'ok':          True,
            'user_id':     emp.user_id.id,
            'user_active': emp.user_id.active,
        })

    @http.route('/api/v1/hr/employees/<int:employee_id>/user', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_employee_user(self, employee_id, **kw):
        emp = request.env['hr.employee'].sudo().browse(employee_id)
        if not emp.exists() or not emp.user_id:
            return http_response({'error': 'employee or linked user not found'}, 404)
        if emp.user_id.id in (1, 2):
            return http_response({'error': 'لا يمكن حذف حساب النظام'}, 403)
        user = emp.user_id.sudo()
        emp.sudo().write({'user_id': False})
        user.write({'active': False})
        return http_response({'ok': True})

    @http.route('/api/v1/hr/employees', type='http', auth='user', methods=['POST'], csrf=False)
    def create_one(self, **kw):
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)

        name = (body.get('name') or '').strip()
        if not name:
            return http_response({'error': 'name is required'}, 400)

        VALID_ROLES  = ('doctor', 'nurse', 'receptionist', 'pharmacist', 'lab_tech', 'rad_tech')
        VALID_GRADES = ('consultant', 'specialist')

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
        if body.get('medical_role') in VALID_ROLES:
            vals['medical_role'] = body['medical_role']
        if body.get('doctor_grade') in VALID_GRADES:
            vals['doctor_grade'] = body['doctor_grade']
        if body.get('specialty_id'):
            vals['specialty_id'] = int(body['specialty_id'])
        if body.get('nurse_specialty_ids'):
            vals['nurse_specialty_ids'] = [(6, 0, [int(i) for i in body['nurse_specialty_ids']])]

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
            'medical_role':    rec.medical_role or '',
            'doctor_grade':    rec.doctor_grade or '',
            'specialty_id':    rec.specialty_id.id if rec.specialty_id else None,
            'specialty_name':  rec.specialty_id.name if rec.specialty_id else '',
            'nurse_specialty_ids':   rec.nurse_specialty_ids.ids,
            'nurse_specialty_names': [s.name for s in rec.nurse_specialty_ids],
            'user_id':         None,
            'user_name':       None,
            'user_login':      None,
            'user_active':     None,
            'active':          True,
        })

    @http.route('/api/v1/hr/employees/<int:employee_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_one(self, employee_id, **kw):
        """Edit an existing employee's medical role/grade/specialty — creation
        (create_one above) was previously the only place these could be set,
        so a doctor added without a grade, or assigned to a specialty later,
        had no way to get one afterwards."""
        rec = request.env['hr.employee'].sudo().browse(employee_id)
        if not rec.exists():
            return http_response({'error': 'employee not found'}, 404)
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return http_response({'error': 'invalid JSON'}, 400)

        VALID_ROLES  = ('doctor', 'nurse', 'receptionist', 'pharmacist', 'lab_tech', 'rad_tech')
        VALID_GRADES = ('consultant', 'specialist')

        vals = {}
        if body.get('name'):
            vals['name'] = str(body['name']).strip()
        if 'work_email' in body:
            vals['work_email'] = str(body['work_email'] or '')
        if 'work_phone' in body:
            vals['work_phone'] = str(body['work_phone'] or '')
        if 'medical_role' in body:
            vals['medical_role'] = body['medical_role'] if body['medical_role'] in VALID_ROLES else False
        if 'doctor_grade' in body:
            vals['doctor_grade'] = body['doctor_grade'] if body['doctor_grade'] in VALID_GRADES else False
        if 'specialty_id' in body:
            vals['specialty_id'] = int(body['specialty_id']) if body['specialty_id'] else False
        if 'nurse_specialty_ids' in body:
            vals['nurse_specialty_ids'] = [(6, 0, [int(i) for i in (body['nurse_specialty_ids'] or [])])]

        if vals:
            rec.write(vals)

        return http_response({
            'id':              rec.id,
            'name':            rec.name,
            'work_email':      rec.work_email or '',
            'work_phone':      rec.work_phone or '',
            'medical_role':    rec.medical_role or '',
            'doctor_grade':    rec.doctor_grade or '',
            'specialty_id':    rec.specialty_id.id if rec.specialty_id else None,
            'specialty_name':  rec.specialty_id.name if rec.specialty_id else '',
            'nurse_specialty_ids':   rec.nurse_specialty_ids.ids,
            'nurse_specialty_names': [s.name for s in rec.nurse_specialty_ids],
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
