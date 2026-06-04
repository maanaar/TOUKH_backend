# -*- coding: utf-8 -*-
import json
from odoo.http import Response


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
    )


def _patient_dict(p):
    return {
        'id':                p.id,
        'name':              p.name or '',
        'first_name':        p.first_name or '',
        'second_name':       p.second_name or '',
        'third_name':        p.third_name or '',
        'last_name':         p.last_name or '',
        'mrn':               getattr(p, 'mrn', '') or '',
        'patient_type':      p.patient_type or 'normal',
        'id_type':           p.id_type or 'national_id',
        'id_number':         p.id_number or '',
        'dob':               str(p.dob) if p.dob else None,
        'gender':            p.gender or '',
        'mobile':            p.phone or '',
        'home_phone':        p.home_phone or '',
        'phone':             p.phone or '',
        'occupation':        p.occupation or '',
        'nationality':       p.country_id.name if p.country_id else '',
        'governorate':       p.governorate or '',
        'city':              p.city or '',
        'street':            p.street or '',
        'financial_class':   p.financial_class or 'cash',
        'insurance_company': p.insurance_company or '',
        'contract_entity':   p.contract_entity or '',
        'image_url':         '/web/image/res.partner/%d/image_1920' % p.id if p.image_1920 else '',
    }
