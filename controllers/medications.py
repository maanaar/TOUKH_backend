# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request
from odoo.fields import Datetime as DT
from .utils import _json


def _med_dict(m):
    return {
        'id':                 m.id,
        'visit_id':           m.visit_id.id if m.visit_id else None,
        'patient_id':         m.patient_id.id if m.patient_id else None,
        'patient_name':       m.patient_id.name if m.patient_id else '',
        'patient_mrn':        (getattr(m.patient_id, 'mrn', '') or '') if m.patient_id else '',
        'patient_national_id': (getattr(m.patient_id, 'id_number', '') or '') if m.patient_id else '',
        'patient_mobile':      (
            getattr(m.patient_id, 'mobile', '')
            or getattr(m.patient_id, 'phone', '')
            or ''
        ) if m.patient_id else '',
        'visit_reference':    m.visit_id.name if m.visit_id else '',
        'financial_class':    m.visit_id.financial_class if m.visit_id else '',
        'specialty_id':       m.visit_id.specialty_id.id if (m.visit_id and m.visit_id.specialty_id) else None,
        'specialty_name':     m.visit_id.specialty_id.name if (m.visit_id and m.visit_id.specialty_id) else '',
        'doctor_id':          (
            m.visit_id.doctor_id.id
            if (m.visit_id and m.visit_id.doctor_id)
            else (m.prescribed_by.id if m.prescribed_by else None)
        ),
        'doctor_name':        (
            m.visit_id.doctor_id.name
            if (m.visit_id and m.visit_id.doctor_id)
            else (m.prescribed_by.name if m.prescribed_by else '')
        ),
        'product_id':         m.product_id.id if m.product_id else None,
        'product_name':       m.product_id.name if m.product_id else '',
        'drug_name':          m.drug_name or (m.product_id.name if m.product_id else ''),
        'dose':               m.dose or '',
        'frequency':          m.frequency or '',
        'duration':           m.duration or '',
        'route':              m.route or 'oral',
        'instructions':       m.instructions or '',
        'quantity':           m.quantity,
        'uom_id':             m.uom_id.id if m.uom_id else None,
        'uom_name':           m.uom_id.name if m.uom_id else '',
        'state':              m.state,
        'cancel_reason':      m.cancel_reason or '',
        'prescribed_by':      m.prescribed_by.id if m.prescribed_by else None,
        'prescribed_by_name': m.prescribed_by.name if m.prescribed_by else '',
        'prescribed_at':      str(m.prescribed_at) if m.prescribed_at else None,
        'dispensed_by':       m.dispensed_by.id if m.dispensed_by else None,
        'dispensed_by_name':  m.dispensed_by.name if m.dispensed_by else '',
        'dispensed_at':       str(m.dispensed_at) if m.dispensed_at else None,
        'dispense_picking_id': m.dispense_picking_id.id if m.dispense_picking_id else None,
        'dispense_picking_name': m.dispense_picking_id.name if m.dispense_picking_id else '',
    }


class MedicationOrderController(http.Controller):

    @http.route('/saycare/api/visit/<int:visit_id>/medications', type='http', auth='user', methods=['GET'], csrf=False)
    def get_by_visit(self, visit_id, **kw):
        records = request.env['saycare.medication.order'].sudo().search(
            [('visit_id', '=', visit_id)]
        )
        return _json([_med_dict(m) for m in records])

    @http.route('/saycare/api/visit/<int:visit_id>/medications', type='http', auth='user', methods=['POST'], csrf=False)
    def create(self, visit_id, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        if not body.get('drug_name') and not body.get('product_id'):
            return _json({'error': 'drug_name or product_id is required'}, 400)

        visit = request.env['saycare.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return _json({'error': 'visit not found'}, 404)

        patient_id = body.get('patient_id') or visit.patient_id.id
        if not patient_id:
            return _json({'error': 'visit has no patient'}, 400)

        prescribed_by = body.get('prescribed_by')
        if not prescribed_by and visit.doctor_id:
            prescribed_by = visit.doctor_id.id

        if not prescribed_by:
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', request.env.user.id)],
                limit=1,
            )
            if employee:
                prescribed_by = employee.id

        vals = {
            'visit_id':      visit.id,
            'patient_id':    patient_id,
            'product_id':    body.get('product_id'),
            'drug_name':     body.get('drug_name', ''),
            'dose':          body.get('dose', ''),
            'frequency':     body.get('frequency', ''),
            'duration':      body.get('duration', ''),
            'route':         body.get('route', 'oral'),
            'instructions':  body.get('instructions', ''),
            'quantity':      body.get('quantity', 1.0),
            'uom_id':        body.get('uom_id'),
            'prescribed_by': prescribed_by,
        }

        try:
            rec = request.env['saycare.medication.order'].sudo().create(vals)
        except Exception as exc:
            request.env.cr.rollback()
            return _json({
                'error': 'failed to create medication order',
                'details': str(exc),
            }, 400)

        return _json(_med_dict(rec), 201)

    @http.route('/saycare/api/visit/<int:visit_id>/medications/<int:med_id>/cancel',
                type='http', auth='user', methods=['POST'], csrf=False)
    def cancel(self, visit_id, med_id, **kw):
        med = request.env['saycare.medication.order'].sudo().browse(med_id)
        if not med.exists() or med.visit_id.id != visit_id:
            return _json({'error': 'medication order not found'}, 404)
        if med.state == 'dispensed':
            return _json({'error': 'cannot cancel a dispensed order'}, 400)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            body = {}
        med.write({'state': 'cancelled', 'cancel_reason': body.get('cancel_reason', '')})
        return _json(_med_dict(med))

    @http.route('/saycare/api/visit/<int:visit_id>/medications/<int:med_id>/dispense',
                type='http', auth='user', methods=['POST'], csrf=False)
    def dispense(self, visit_id, med_id, **kw):
        med = request.env['saycare.medication.order'].sudo().browse(med_id)
        if not med.exists() or med.visit_id.id != visit_id:
            return _json({'error': 'medication order not found'}, 404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            body = {}

        picking = False
        picking_id = body.get('picking_id')
        if picking_id:
            try:
                picking = request.env['stock.picking'].sudo().browse(int(picking_id))
            except (TypeError, ValueError):
                return _json({'error': 'invalid picking_id'}, 400)

            if not picking.exists():
                return _json({'error': 'dispense picking not found'}, 404)
            if picking.state != 'done':
                return _json({'error': 'dispense picking must be validated first'}, 400)

        # Retry-safe behavior: return the already-dispensed record instead of
        # creating another stock movement or failing the whole user workflow.
        if med.state == 'dispensed':
            if (
                picking
                and med.dispense_picking_id
                and med.dispense_picking_id.id != picking.id
            ):
                return _json(
                    {'error': 'medication is already linked to another dispense picking'},
                    409,
                )

            if picking and not med.dispense_picking_id:
                med.write({'dispense_picking_id': picking.id})

            return _json(_med_dict(med))

        if med.state != 'active':
            return _json({'error': 'only active orders can be dispensed'}, 400)

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)],
            limit=1,
        )

        vals = {
            'state': 'dispensed',
            'dispensed_at': DT.now(),
        }

        if employee:
            vals['dispensed_by'] = employee.id
        elif body.get('dispensed_by'):
            # Transitional fallback for users not yet linked to hr.employee.
            vals['dispensed_by'] = body.get('dispensed_by')

        if picking:
            vals['dispense_picking_id'] = picking.id

        med.write(vals)

        # Legacy compatibility only: callers that do not provide picking_id
        # retain the previous stock-move behavior. The active SayCare Pharmacy
        # flow provides picking_id and therefore never moves stock twice.
        if not picking and med.product_id and med.quantity:
            # A caller may still edit the dispensed quantity without going
            # through the picking-based flow — honor it here too, falling
            # back to the originally prescribed quantity.
            try:
                dispensed_qty = float(body.get('quantity')) if body.get('quantity') not in (None, '') else med.quantity
            except (TypeError, ValueError):
                dispensed_qty = med.quantity

            warehouse = request.env['stock.warehouse'].sudo().search(
                [('company_id', '=', request.env.company.id)],
                limit=1,
            )
            move = request.env['stock.move'].sudo().create({
                'name':             med.drug_name or med.product_id.name,
                'product_id':       med.product_id.id,
                'product_uom_qty':  dispensed_qty,
                'product_uom':      (med.uom_id or med.product_id.uom_id).id,
                'location_id':      warehouse.lot_stock_id.id,
                'location_dest_id': request.env.ref('stock.location_production').id,
            })
            move._action_confirm()
            move._action_assign()
            move.write({'quantity': dispensed_qty})
            move._action_done()

        return _json(_med_dict(med))


class PharmacyQueueController(http.Controller):

    @http.route('/saycare/api/pharmacy/queue', type='http', auth='user', methods=['GET'], csrf=False)
    def queue(self, date_from='', date_to='', **kw):
        if date_from:
            try:
                range_start = datetime.strptime(date_from, '%Y-%m-%d').replace(hour=0,  minute=0,  second=0)
                range_end   = datetime.strptime(date_to or date_from, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                range_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                range_end   = range_start + timedelta(days=1)
        else:
            range_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            range_end   = range_start + timedelta(days=1)

        records = request.env['saycare.medication.order'].sudo().search([
            ('prescribed_at', '>=', str(range_start)),
            ('prescribed_at', '<=', str(range_end)),
        ], order='prescribed_at asc')
        return _json([_med_dict(m) for m in records])


class PharmacyDirectOrderController(http.Controller):

    @http.route('/saycare/api/pharmacy/direct-order', type='http', auth='user', methods=['POST'], csrf=False)
    def direct_order(self, **kw):
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json({'error': 'invalid JSON'}, 400)

        # ── Resolve patient ───────────────────────────────────────────────────
        patient = None
        if body.get('patient_id'):
            patient = request.env['res.partner'].sudo().browse(body['patient_id'])
            if not patient.exists() or not patient.is_patient:
                return _json({'error': 'patient not found'}, 404)
        elif body.get('new_patient'):
            np = body['new_patient']
            name = (np.get('name') or '').strip()
            if not name:
                return _json({'error': 'new_patient.name is required'}, 400)
            patient = request.env['res.partner'].sudo().create({
                'name':       name,
                'is_patient': True,
                'phone':      np.get('phone', '') or np.get('mobile', ''),
            })
        else:
            return _json({'error': 'patient_id or new_patient is required'}, 400)

        medications = body.get('medications', [])
        if not medications:
            return _json({'error': 'medications list is required'}, 400)

        # ── Create medication orders ──────────────────────────────────────────
        orders = []
        for m in medications:
            vals = {
                'patient_id':    patient.id,
                'product_id':    m.get('product_id'),
                'drug_name':     m.get('drug_name', ''),
                'dose':          m.get('dose', ''),
                'frequency':     m.get('frequency', ''),
                'duration':      m.get('duration', ''),
                'route':         m.get('route', 'oral'),
                'instructions':  m.get('instructions', ''),
                'quantity':      m.get('quantity', 1.0),
                'uom_id':        m.get('uom_id'),
                'prescribed_by': body.get('prescribed_by'),
                'state':         'active',
            }
            rec = request.env['saycare.medication.order'].sudo().create(vals)
            orders.append(_med_dict(rec))

        return _json({
            'patient': {
                'id':     patient.id,
                'name':   patient.name,
                'mrn':    getattr(patient, 'mrn', '') or '',
                'mobile': patient.phone or '',
            },
            'orders': orders,
        }, 201)
