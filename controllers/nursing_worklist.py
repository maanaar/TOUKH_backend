# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.http import request
from .utils import _json


def _load_body():
    """Return (body_dict, error_response). error_response is None on success."""
    try:
        return json.loads(request.httprequest.data or '{}'), None
    except json.JSONDecodeError:
        return None, _json({'error': 'invalid JSON'}, 400)


def _dt_iso(v):
    if not v:
        return ''
    return v.strftime('%Y-%m-%dT%H:%M')


NURSE_VALID_TRANSITIONS = {
    'pending':   ['accepted', 'held'],
    'accepted':  ['completed', 'held'],
    'held':      ['accepted'],
    'completed': [],
}

ACTION_TO_STATUS = {
    'accept':   'accepted',
    'complete': 'completed',
    'hold':     'held',
}

SOURCE_MODELS = {
    'medication': 'saycare.medication.order',
    'lab':        'saycare.lab.order',
    'rad':        'saycare.rad.order',
}


def _task_from_medication(m):
    return {
        'id':           m.id,
        'sourceType':   'medication',
        'sourceModel':  'saycare.medication.order',
        'taskType':     'medication',
        'taskName':     ' '.join(filter(None, [m.drug_name, m.dose, m.frequency])).strip(),
        'orderSource':  'أمر دوائي',
        'priority':     'routine',
        'status':       m.state or '',
        'nurseStatus':  m.nurse_status or 'pending',
        'dueAt':        _dt_iso(m.prescribed_at),
    }


def _task_from_lab(lo):
    return {
        'id':           lo.id,
        'sourceType':   'lab',
        'sourceModel':  'saycare.lab.order',
        'taskType':     'lab',
        'taskName':     lo.test_name or '',
        'orderSource':  'أمر مخبري',
        'priority':     lo.priority or 'routine',
        'status':       lo.state or '',
        'nurseStatus':  lo.nurse_status or 'pending',
        'dueAt':        _dt_iso(lo.requested_at),
    }


def _task_from_rad(ro):
    return {
        'id':           ro.id,
        'sourceType':   'rad',
        'sourceModel':  'saycare.rad.order',
        'taskType':     'rad',
        'taskName':     ro.study_type or '',
        'orderSource':  'أمر أشعة',
        'priority':     'routine',
        'status':       ro.state or '',
        'nurseStatus':  ro.nurse_status or 'pending',
        'dueAt':        _dt_iso(ro.requested_at),
    }


def _resolve_visit(admission):
    """Return the saycare.visit tied to this admission, resolving + self-healing
    the link for legacy records booked before `visit_id` existed."""
    if admission.visit_id:
        return admission.visit_id
    if not admission.patient_id:
        return request.env['saycare.visit']
    visit = request.env['saycare.visit'].sudo().search([
        ('patient_id', '=', admission.patient_id.id),
        ('visit_type', '=', 'inpatient'),
    ], order='admission_date desc', limit=1)
    if visit:
        admission.write({'visit_id': visit.id})
    return visit


class NursingWorklistController(http.Controller):

    @http.route('/saycare/api/admission-requests/<int:rec_id>/nursing-worklist',
                type='http', auth='user', methods=['GET'], csrf=False)
    def get_worklist(self, rec_id, **kw):
        admission = request.env['saycare.admission.request'].sudo().browse(rec_id)
        if not admission.exists():
            return _json({'error': 'admission request not found'}, 404)

        patient = {
            'patientName':            admission.patient_name or '',
            'patientMrn':             admission.patient_mrn or admission.x_file_number or '',
            'inpatientBookingNumber': admission.inpatient_booking_number or '',
            'operationBookingNumber': admission.operation_booking_number or '',
            'ward':                   admission.ward or '',
            'roomName':               admission.room_id.display_name if admission.room_id else '',
            'bedName':                admission.bed_id.display_name if admission.bed_id else '',
            'status':                 admission.status or '',
            'worklistStage':          admission.worklist_stage or 'booked',
            'billTotal':              admission.sale_order_id.amount_total if admission.sale_order_id else 0.0,
        }

        visit = _resolve_visit(admission)
        tasks = []
        if visit:
            tasks += [_task_from_medication(m) for m in visit.medication_order_ids]
            tasks += [_task_from_lab(lo) for lo in visit.lab_order_ids]
            tasks += [_task_from_rad(ro) for ro in visit.rad_order_ids]

        stats = {
            'transferPrep':     0,
            'samplesPending':   sum(1 for t in tasks if t['taskType'] == 'lab' and t['nurseStatus'] != 'completed'),
            'medicationsDue':   sum(1 for t in tasks if t['taskType'] == 'medication' and t['nurseStatus'] != 'completed'),
            'pendingTasks':     sum(1 for t in tasks if t['nurseStatus'] == 'pending'),
        }

        return _json({'patient': patient, 'stats': stats, 'tasks': tasks})

    @http.route('/saycare/api/nursing-tasks/<string:source_type>/<int:task_id>/action',
                type='http', auth='user', methods=['POST'], csrf=False)
    def set_task_action(self, source_type, task_id, **kw):
        model_name = SOURCE_MODELS.get(source_type)
        if not model_name:
            return _json({'error': 'unknown task source type'}, 404)

        rec = request.env[model_name].sudo().browse(task_id)
        if not rec.exists():
            return _json({'error': 'task not found'}, 404)

        body, err = _load_body()
        if err:
            return err

        action = body.get('action')
        target_status = ACTION_TO_STATUS.get(action)
        if not target_status:
            return _json({'error': 'unknown action'}, 400)

        current_status = rec.nurse_status or 'pending'
        if target_status not in NURSE_VALID_TRANSITIONS.get(current_status, []):
            return _json({'error': f'cannot transition from {current_status} to {target_status}'}, 400)

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1,
        )
        vals = {
            'nurse_status':    target_status,
            'nurse_status_at': fields.Datetime.now(),
        }
        if employee:
            vals['nurse_status_by'] = employee.id
        rec.write(vals)

        task_builders = {
            'medication': _task_from_medication,
            'lab':        _task_from_lab,
            'rad':        _task_from_rad,
        }
        return _json(task_builders[source_type](rec))
