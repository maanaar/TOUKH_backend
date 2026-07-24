# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request

def _json(data, status=200):
    return request.make_response(
        json.dumps(data, default=str),
        headers=[('Content-Type', 'application/json; charset=utf-8')],
        status=status,
    )

def _load_body():
    """Return (body_dict, error_response). error_response is None on success."""
    try:
        return json.loads(request.httprequest.data or '{}'), None
    except json.JSONDecodeError:
        return None, _json({'error': 'invalid JSON'}, 400)

def _query_bool(value):
    normalized = str(value or '').strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return None


def _department_dict(r):
    return {
        'id':              r.id,
        'code':            r.code or '',
        'name_ar':         r.name_ar or '',
        'name_en':         r.name_en or '',
        'main_specialty':  r.main_specialty or '',
        'ward_type':       r.ward_type or '',
        'manager_id':      r.manager_id.id if r.manager_id else None,
        'manager_name':    r.manager_id.display_name if r.manager_id else '',
        'head_nurse_id':   r.head_nurse_id.id if r.head_nurse_id else None,
        'head_nurse_name': r.head_nurse_id.display_name if r.head_nurse_id else '',
        'floor_count':     r.floor_count,
        'bed_count':       r.bed_count,
        'active':          r.active,
        'care':            r.care,
        'notes':           r.notes or '',
        'image_url':       f'/web/image/hospital.inpatient.department/{r.id}/image' if r.image else '',
    }


def _floor_dict(r):
    first_dept = r.department_ids[:1]
    return {
        'id':               r.id,
        'code':             r.code or '',
        'name':             r.name or '',
        'building':         r.building or '',
        'floor_no':         r.floor_no or '',
        'department_ids':   r.department_ids.ids,
        'department_names': [d.display_name for d in r.department_ids],
        # kept for callers still expecting a single department (first linked one)
        'department_id':    first_dept.id if first_dept else None,
        'department_name':  first_dept.display_name if first_dept else '',
        'active':           r.active,
        'notes':            r.notes or '',
    }


def _room_dict(r):
    return {
        'id':              r.id,
        'code':            r.code or '',
        'room_no':         r.room_no or '',
        'floor_id':        r.floor_id.id if r.floor_id else None,
        'floor_name':      r.floor_id.display_name if r.floor_id else '',
        'department_id':   r.department_id.id if r.department_id else None,
        'department_name': r.department_id.display_name if r.department_id else '',
        'room_type':       r.room_type or '',
        'allowed_gender':  r.allowed_gender or '',
        'capacity':        r.capacity,
        'bed_count':       r.bed_count,
        'room_status':     r.room_status or '',
        'active':          r.active,
    }


def _grade_type_dict(r):
    return {
        'id':   r.id,
        'name': r.name or '',
    }


def _grade_dict(r):
    return {
        'id':                 r.id,
        'code':               r.code or '',
        'name':               r.name.display_name if r.name else '',
        'name_id':            r.name.id if r.name else None,
        'accommodation_type': r.accommodation_type or '',
        'price_per_day':      r.price_per_day,
        'include_nursing':    r.include_nursing,
        'include_meals':      r.include_meals,
        'need_approval':      r.need_approval,
        'active':             r.active,
    }


def _bed_dict(r):
    return {
        'id':                   r.id,
        'code':                 r.code or '',
        'bed_no':               r.bed_no or '',
        'room_id':              r.room_id.id if r.room_id else None,
        'room_name':            r.room_id.display_name if r.room_id else '',
        'room_type':            r.room_id.room_type if r.room_id else '',
        'floor_id':             r.floor_id.id if r.floor_id else None,
        'floor_name':           r.floor_id.display_name if r.floor_id else '',
        'department_id':        r.department_id.id if r.department_id else None,
        'department_name':      r.department_id.display_name if r.department_id else '',
        'grade_id':             r.grade_id.id if r.grade_id else None,
        'grade_name':           r.grade_id.display_name if r.grade_id else '',
        'bed_status':           r.bed_status or '',
        'allowed_gender':       r.allowed_gender or '',
        'current_patient_id':   r.current_patient_id.id if r.current_patient_id else None,
        'current_patient_name': r.current_patient_id.display_name if r.current_patient_id else '',
        'last_occupancy_date':  r.last_occupancy_date.isoformat() if r.last_occupancy_date else '',
        'has_ventilator':       r.has_ventilator,
        'active':               r.active,
    }


class DepartmentController(http.Controller):
    _model = 'hospital.inpatient.department'

    @http.route('/saycare/api/departments', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, specialty='', ward_type='', care='', **kw):
        domain = [('active', '=', True)]
        if specialty:
            domain.append(('main_specialty', '=', specialty))
        if ward_type:
            domain.append(('ward_type', '=', ward_type))
        care_filter = _query_bool(care)
        if care_filter is not None:
            domain.append(('care', '=', care_filter))
        records = request.env[self._model].sudo().search(domain)
        return _json([_department_dict(r) for r in records])

    @http.route('/saycare/api/departments/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'department not found'}, 404)
        return _json(_department_dict(rec))

    @http.route('/saycare/api/departments', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        if not body.get('code') or not body.get('name_ar'):
            return _json({'error': 'code and name_ar are required'}, 400)
        vals = {
            'code':           body['code'],
            'name_ar':        body['name_ar'],
            'name_en':        body.get('name_en', ''),
            'main_specialty': body.get('main_specialty'),
            'ward_type':      body.get('ward_type'),
            'notes':          body.get('notes', ''),
        }
        for f in ('manager_id', 'head_nurse_id'):
            if body.get(f):
                vals[f] = int(body[f])
        rec = request.env[self._model].sudo().create(vals)
        return _json(_department_dict(rec), 201)

    @http.route('/saycare/api/departments/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'department not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = {}
        for f in ('code', 'name_ar', 'name_en', 'main_specialty', 'ward_type', 'notes', 'active'):
            if f in body:
                vals[f] = body[f]
        for f in ('manager_id', 'head_nurse_id'):
            if f in body:
                vals[f] = int(body[f]) if body[f] else False
        if vals:
            rec.write(vals)
        return _json(_department_dict(rec))

    @http.route('/saycare/api/departments/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'department not found'}, 404)
        rec.write({'active': False})
        return _json({'deleted': True, 'id': rec_id})


class FloorController(http.Controller):
    _model = 'hospital.floor'

    @http.route('/saycare/api/floors', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, department_id='', **kw):
        domain = [('active', '=', True)]
        if department_id:
            domain.append(('department_ids', 'in', [int(department_id)]))
        records = request.env[self._model].sudo().search(domain)
        return _json([_floor_dict(r) for r in records])

    @http.route('/saycare/api/floors/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'floor not found'}, 404)
        return _json(_floor_dict(rec))

    @http.route('/saycare/api/floors', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        department_ids = body.get('department_ids') or ([body['department_id']] if body.get('department_id') else [])
        if not body.get('code') or not body.get('name') or not department_ids:
            return _json({'error': 'code, name and department_ids are required'}, 400)
        vals = {
            'code':           body['code'],
            'name':           body['name'],
            'building':       body.get('building', ''),
            'floor_no':       body.get('floor_no', ''),
            'department_ids': [(6, 0, [int(d) for d in department_ids])],
            'notes':          body.get('notes', ''),
        }
        rec = request.env[self._model].sudo().create(vals)
        return _json(_floor_dict(rec), 201)

    @http.route('/saycare/api/floors/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'floor not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = {}
        for f in ('code', 'name', 'building', 'floor_no', 'notes', 'active'):
            if f in body:
                vals[f] = body[f]
        if 'department_ids' in body:
            vals['department_ids'] = [(6, 0, [int(d) for d in (body['department_ids'] or [])])]
        elif 'department_id' in body:
            vals['department_ids'] = [(6, 0, [int(body['department_id'])] if body['department_id'] else [])]
        if vals:
            rec.write(vals)
        return _json(_floor_dict(rec))

    @http.route('/saycare/api/floors/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'floor not found'}, 404)
        rec.write({'active': False})
        return _json({'deleted': True, 'id': rec_id})

class RoomController(http.Controller):
    _model = 'hospital.room'

    @http.route('/saycare/api/rooms', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, floor_id='', department_id='', room_status='', room_type='', care='', **kw):
        domain = [('active', '=', True)]
        if floor_id:
            domain.append(('floor_id', '=', int(floor_id)))
        if department_id:
            domain.append(('department_id', '=', int(department_id)))
        if room_status:
            domain.append(('room_status', '=', room_status))
        if room_type:
            types = [t.strip() for t in room_type.split(',') if t.strip()]
            domain.append(('room_type', 'in', types) if len(types) > 1 else ('room_type', '=', types[0]))
        care_filter = _query_bool(care)
        if care_filter is True:
            domain.append(('department_id.care', '=', True))
        elif care_filter is False:
            domain.append('|')
            domain.append(('department_id', '=', False))
            domain.append(('department_id.care', '=', False))
        records = request.env[self._model].sudo().search(domain)
        return _json([_room_dict(r) for r in records])

    @http.route('/saycare/api/rooms/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'room not found'}, 404)
        return _json(_room_dict(rec))

    @http.route('/saycare/api/rooms', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        required = ('code', 'room_no', 'floor_id', 'room_type')
        if not all(body.get(f) for f in required):
            return _json({'error': 'code, room_no, floor_id and room_type are required'}, 400)
        vals = {
            'code':           body['code'],
            'room_no':        body['room_no'],
            'floor_id':       int(body['floor_id']),
            'room_type':      body['room_type'],
            'allowed_gender': body.get('allowed_gender', 'all'),
            'capacity':       int(body['capacity']) if body.get('capacity') else 0,
            'room_status':    body.get('room_status', 'available'),
        }
        # القسم بيتحسب تلقائي من أول قسم مرتبط بالدور، لكن الدور ممكن يكون
        # فيه أكتر من قسم — فلو الطلب حدد department_id صراحة (مثلاً الغرفة
        # دي مخصصة لقسم تاني غير اللي هيتحط تلقائي)، نستخدمه.
        if body.get('department_id'):
            vals['department_id'] = int(body['department_id'])
        rec = request.env[self._model].sudo().create(vals)
        return _json(_room_dict(rec), 201)

    @http.route('/saycare/api/rooms/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'room not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = {}
        for f in ('code', 'room_no', 'room_type', 'allowed_gender', 'room_status', 'active'):
            if f in body:
                vals[f] = body[f]
        if 'capacity' in body:
            vals['capacity'] = int(body['capacity']) if body['capacity'] else 0
        if 'floor_id' in body:
            vals['floor_id'] = int(body['floor_id']) if body['floor_id'] else False
        if 'department_id' in body:
            vals['department_id'] = int(body['department_id']) if body['department_id'] else False
        if vals:
            rec.write(vals)
        return _json(_room_dict(rec))

    @http.route('/saycare/api/rooms/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'room not found'}, 404)
        rec.write({'active': False})
        return _json({'deleted': True, 'id': rec_id})


class GradeTypeController(http.Controller):
    _model = 'hospital.accommodation.grade.type'

    @http.route('/saycare/api/accommodation-grade-types', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env[self._model].sudo().search([('active', '=', True)])
        return _json([_grade_type_dict(r) for r in records])


class GradeController(http.Controller):
    _model = 'hospital.accommodation.grade'

    @http.route('/saycare/api/accommodation-grades', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, **kw):
        records = request.env[self._model].sudo().search([('active', '=', True)])
        return _json([_grade_dict(r) for r in records])

    @http.route('/saycare/api/accommodation-grades/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'grade not found'}, 404)
        return _json(_grade_dict(rec))

    @http.route('/saycare/api/accommodation-grades', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        name_id = body.get('name_id', body.get('name'))
        if not body.get('code') or not name_id:
            return _json({'error': 'code and name (grade type id) are required'}, 400)
        vals = {
            'code':               body['code'],
            'name':               int(name_id),
            'accommodation_type': body.get('accommodation_type', ''),
            'price_per_day':      float(body['price_per_day']) if body.get('price_per_day') else 0.0,
            'include_nursing':    bool(body.get('include_nursing')),
            'include_meals':      bool(body.get('include_meals')),
            'need_approval':      bool(body.get('need_approval')),
        }
        rec = request.env[self._model].sudo().create(vals)
        return _json(_grade_dict(rec), 201)

    @http.route('/saycare/api/accommodation-grades/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'grade not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = {}
        for f in ('code', 'accommodation_type', 'active'):
            if f in body:
                vals[f] = body[f]
        if 'name_id' in body:
            vals['name'] = int(body['name_id']) if body['name_id'] else False
        elif 'name' in body:
            vals['name'] = int(body['name']) if body['name'] else False
        if 'price_per_day' in body:
            vals['price_per_day'] = float(body['price_per_day']) if body['price_per_day'] else 0.0
        for f in ('include_nursing', 'include_meals', 'need_approval'):
            if f in body:
                vals[f] = bool(body[f])
        if vals:
            rec.write(vals)
        return _json(_grade_dict(rec))

    @http.route('/saycare/api/accommodation-grades/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'grade not found'}, 404)
        rec.write({'active': False})
        return _json({'deleted': True, 'id': rec_id})


class BedController(http.Controller):
    _model = 'hospital.bed'

    @http.route('/saycare/api/beds', type='http', auth='user', methods=['GET'], csrf=False)
    def get_all(self, room_id='', floor_id='', department_id='', bed_status='', grade_id='', room_type='', care='', **kw):
        domain = [('active', '=', True)]
        if room_id:
            domain.append(('room_id', '=', int(room_id)))
        if floor_id:
            domain.append(('floor_id', '=', int(floor_id)))
        if department_id:
            domain.append(('department_id', '=', int(department_id)))
        if bed_status:
            domain.append(('bed_status', '=', bed_status))
        if grade_id:
            domain.append(('grade_id', '=', int(grade_id)))
        if room_type:
            types = [t.strip() for t in room_type.split(',') if t.strip()]
            domain.append(('room_id.room_type', 'in', types) if len(types) > 1 else ('room_id.room_type', '=', types[0]))
        care_filter = _query_bool(care)
        if care_filter is True:
            domain.append(('department_id.care', '=', True))
        elif care_filter is False:
            domain.append('|')
            domain.append(('department_id', '=', False))
            domain.append(('department_id.care', '=', False))
        records = request.env[self._model].sudo().search(domain)
        return _json([_bed_dict(r) for r in records])

    @http.route('/saycare/api/beds/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_one(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'bed not found'}, 404)
        return _json(_bed_dict(rec))

    @http.route('/saycare/api/beds', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, **kw):
        body, err = _load_body()
        if err:
            return err
        if not body.get('code') or not body.get('bed_no') or not body.get('room_id'):
            return _json({'error': 'code, bed_no and room_id are required'}, 400)
        room = request.env['hospital.room'].sudo().browse(int(body['room_id']))
        vals = {
            'code':           body['code'],
            'bed_no':         body['bed_no'],
            'room_id':        room.id,
            # floor/department are manually settable, but default to the room's own
            # so a bed isn't silently left without them when the caller omits these.
            'floor_id':       int(body['floor_id']) if body.get('floor_id') else (room.floor_id.id or False),
            'department_id':  int(body['department_id']) if body.get('department_id') else (room.department_id.id or False),
            'bed_status':     body.get('bed_status', 'available'),
            'allowed_gender': body.get('allowed_gender', 'all'),
        }
        if body.get('grade_id'):
            vals['grade_id'] = int(body['grade_id'])
        if body.get('current_patient_id'):
            vals['current_patient_id'] = int(body['current_patient_id'])
        if body.get('last_occupancy_date'):
            vals['last_occupancy_date'] = body['last_occupancy_date']
        if 'has_ventilator' in body:
            vals['has_ventilator'] = bool(body['has_ventilator'])
        rec = request.env[self._model].sudo().create(vals)
        return _json(_bed_dict(rec), 201)

    @http.route('/saycare/api/beds/<int:rec_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'bed not found'}, 404)
        body, err = _load_body()
        if err:
            return err
        vals = {}
        for f in ('code', 'bed_no', 'bed_status', 'allowed_gender', 'last_occupancy_date', 'active'):
            if f in body:
                vals[f] = body[f]
        if 'has_ventilator' in body:
            vals['has_ventilator'] = bool(body['has_ventilator'])
        for f in ('room_id', 'floor_id', 'department_id', 'grade_id', 'current_patient_id'):
            if f in body:
                vals[f] = int(body[f]) if body[f] else False
        # room changed without an explicit floor/department override — follow the room
        if 'room_id' in vals and vals['room_id'] and 'floor_id' not in body and 'department_id' not in body:
            room = request.env['hospital.room'].sudo().browse(vals['room_id'])
            vals['floor_id'] = room.floor_id.id or False
            vals['department_id'] = room.department_id.id or False
        if vals:
            rec.write(vals)
        return _json(_bed_dict(rec))

    @http.route('/saycare/api/beds/<int:rec_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete(self, rec_id, **kw):
        rec = request.env[self._model].sudo().browse(rec_id)
        if not rec.exists():
            return _json({'error': 'bed not found'}, 404)
        rec.write({'active': False})
        return _json({'deleted': True, 'id': rec_id})