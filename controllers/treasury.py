# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from .utils import _json

FINANCIAL_CLASS_AR = {
    'cash':         'نقدي',
    'insurance':    'تأمين صحى',
    'state':        'نفقة الدولة',
    'takaful':      'تكافل وكرامة',
    'consultation': 'مشورة',
    'contract':     'تعاقدات',
    'moh':          'وزارة الصحة',
    'staff':        'عاملين',
}

VISIT_TYPE_AR = {
    'outpatient':   'كشف خارجي',
    'inpatient':    'حجز داخلي',
    'emergency':    'طوارئ',
    'consultation': 'استشارة',
}


class TreasuryController(http.Controller):

    @http.route('/saycare/api/treasury', type='http', auth='user', methods=['GET'], csrf=False)
    def get(self, date='', **kw):
        """
        Returns all visits for the given date with their invoice & payment info.
        date: YYYY-MM-DD  (defaults to today)
        """
        from odoo.fields import Date as D
        target = date or str(D.today())

        visits = request.env['saycare.visit'].sudo().search([
            ('admission_date', '>=', f'{target} 00:00:00'),
            ('admission_date', '<=', f'{target} 23:59:59'),
        ], order='admission_date asc')

        rows = []
        for v in visits:
            inv = getattr(v, 'invoice_id', None) or None
            payment_state = inv.payment_state  if inv else ''
            amount_total  = inv.amount_total   if inv else 0.0
            amount_due    = inv.amount_residual if inv else 0.0

            # When visit has no service_ids (e.g. procedures added via invoice lines),
            # derive shares from the invoice total directly
            v_insurance = getattr(v, 'insurance_share', 0.0) or 0.0
            v_patient   = getattr(v, 'patient_share',   0.0) or 0.0
            if amount_total > 0 and v_insurance == 0 and v_patient == 0:
                fin_class = getattr(v, 'financial_class', 'cash') or 'cash'
                if fin_class == 'cash':
                    v_patient = amount_total
                else:
                    v_patient = amount_total  # invoice already contains only patient share lines

            # pull time from admission_date
            admission_dt = v.admission_date
            time_str = ''
            if admission_dt:
                time_str = f'{admission_dt.hour:02d}:{admission_dt.minute:02d}'

            rows.append({
                'visit_id':          v.id,
                'visit_name':        v.name or '',
                'time':              time_str,
                'patient_id':        v.patient_id.id   if v.patient_id else None,
                'patient_name':      v.patient_id.name if v.patient_id else '—',
                'mrn':               getattr(v.patient_id, 'mrn',       '') if v.patient_id else '',
                'national_id':       getattr(v.patient_id, 'id_number', '') if v.patient_id else '',
                'mobile':            v.patient_id.phone if v.patient_id else '',
                'clinic':            v.specialty_id.name if v.specialty_id else '',
                'doctor':            v.doctor_id.name    if v.doctor_id   else '',
                'visit_type':        VISIT_TYPE_AR.get(v.visit_type or '', v.visit_type or ''),
                'financial_class':   getattr(v, 'financial_class', '') or '',
                'financial_label':   FINANCIAL_CLASS_AR.get(getattr(v, 'financial_class', '') or '', ''),
                'state':             v.state,
                'invoice_id':        inv.id            if inv else None,
                'invoice_name':      inv.name          if inv else '',
                'invoice_state':     inv.state         if inv else '',
                'payment_state':     payment_state,
                'amount_total':      amount_total,
                'amount_due':        amount_due,
                'insurance_share':   v_insurance,
                'patient_share':     v_patient,
            })

        # summary totals
        total_amount = sum(r['amount_total'] for r in rows)
        cash_amount  = sum(r['amount_total'] for r in rows if r['financial_class'] == 'cash')

        return _json({
            'date':         target,
            'rows':         rows,
            'total_visits': len(rows),
            'total_amount': total_amount,
            'cash_amount':  cash_amount,
        })
