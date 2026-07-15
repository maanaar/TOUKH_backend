# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.http import request

from .admission_requests import _admission_request_dict
from .utils import _json


_logger = logging.getLogger(__name__)


def _load_body():
    try:
        body = json.loads(
            request.httprequest.data
            or '{}'
        )

    except json.JSONDecodeError:
        return None, _json(
            {
                'error': 'بيانات الطلب غير صحيحة',
            },
            400,
        )

    if not isinstance(body, dict):
        return None, _json(
            {
                'error': 'بيانات الطلب يجب أن تكون كائنًا',
            },
            400,
        )

    return body, None


def _as_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    return str(value or '').strip().lower() in {
        '1',
        'true',
        'yes',
        'y',
        'on',
    }


def _as_int(value):
    if value in (None, '', False):
        return 0

    return int(value)


def _as_float(value):
    if value in (None, '', False):
        return 0.0

    return float(value)


def _as_text(value):
    if value in (None, False):
        return ''

    return str(value)


def _as_datetime(value):
    if not value:
        return False

    normalized = str(value).replace('T', ' ')

    if len(normalized) == 16:
        normalized += ':00'

    return fields.Datetime.to_datetime(normalized)


_FIELD_MAP = {
    # Receiving information
    'receivingTime': (
        'receiving_time',
        _as_datetime,
    ),
    'receivingShift': (
        'receiving_shift',
        _as_text,
    ),
    'bedConfirmation': (
        'bed_confirmation',
        _as_text,
    ),

    # Initial assessment
    'consciousness': (
        'consciousness',
        _as_text,
    ),
    'orientation': (
        'orientation',
        _as_text,
    ),
    'mobility': (
        'mobility',
        _as_text,
    ),
    'generalCondition': (
        'general_condition',
        _as_text,
    ),
    'painScore': (
        'pain_score',
        _as_int,
    ),
    'weightKg': (
        'weight_kg',
        _as_float,
    ),
    'heightCm': (
        'height_cm',
        _as_float,
    ),
    'requiresIsolation': (
        'requires_isolation',
        _as_bool,
    ),
    'oxygenRequired': (
        'oxygen_required',
        _as_bool,
    ),
    'npo': (
        'npo',
        _as_bool,
    ),
    'highDependency': (
        'high_dependency',
        _as_bool,
    ),
    'doctorToBeNotified': (
        'doctor_to_be_notified',
        _as_bool,
    ),

    # Initial vital signs
    'temperatureC': (
        'temperature_c',
        _as_float,
    ),
    'pulseBpm': (
        'pulse_bpm',
        _as_int,
    ),
    'bloodPressure': (
        'blood_pressure',
        _as_text,
    ),
    'respiratoryRate': (
        'respiratory_rate',
        _as_int,
    ),
    'spo2Percent': (
        'spo2_percent',
        _as_float,
    ),
    'bloodGlucose': (
        'blood_glucose',
        _as_float,
    ),
    'vitalPainScore': (
        'vital_pain_score',
        _as_int,
    ),
    'vitalsRecordedByName': (
        'vitals_recorded_by_name',
        _as_text,
    ),

    # Allergies
    'drugAllergy': (
        'drug_allergy',
        _as_text,
    ),
    'foodAllergy': (
        'food_allergy',
        _as_text,
    ),
    'latexAllergy': (
        'latex_allergy',
        _as_text,
    ),
    'allergyStatus': (
        'allergy_status',
        _as_text,
    ),

    # Infection control
    'isolationType': (
        'isolation_type',
        _as_text,
    ),
    'infectionRisk': (
        'infection_risk',
        _as_text,
    ),
    'ppeRequired': (
        'ppe_required',
        _as_text,
    ),
    'infectionNotes': (
        'infection_notes',
        _as_text,
    ),

    # Risk assessment
    'fallRisk': (
        'fall_risk',
        _as_text,
    ),
    'bradenScaleScore': (
        'braden_scale_score',
        _as_int,
    ),
    'pressureUlcerRisk': (
        'pressure_ulcer_risk',
        _as_text,
    ),
    'nutritionRisk': (
        'nutrition_risk',
        _as_text,
    ),
    'psychologicalSafetyRisk': (
        'psychological_safety_risk',
        _as_text,
    ),
    'dvtRisk': (
        'dvt_risk',
        _as_text,
    ),
    'bleedingRisk': (
        'bleeding_risk',
        _as_text,
    ),
    'riskAction': (
        'risk_action',
        _as_text,
    ),

    # Belongings
    'belongingMobile': (
        'belonging_mobile',
        _as_bool,
    ),
    'belongingMoney': (
        'belonging_money',
        _as_bool,
    ),
    'belongingWatch': (
        'belonging_watch',
        _as_bool,
    ),
    'belongingClothes': (
        'belonging_clothes',
        _as_bool,
    ),
    'belongingDocuments': (
        'belonging_documents',
        _as_bool,
    ),
    'belongingGlasses': (
        'belonging_glasses',
        _as_bool,
    ),
    'belongingDenture': (
        'belonging_denture',
        _as_bool,
    ),
    'belongingOther': (
        'belonging_other',
        _as_bool,
    ),
    'belongingsHandedTo': (
        'belongings_handed_to',
        _as_text,
    ),
    'belongingsRelativeName': (
        'belongings_relative_name',
        _as_text,
    ),
    'belongingsSignatureOrId': (
        'belongings_signature_or_id',
        _as_text,
    ),

    # IV access / lines / drains
    'cannulaStatus': (
        'cannula_status',
        _as_text,
    ),
    'cannulaSite': (
        'cannula_site',
        _as_text,
    ),
    'cannulaSize': (
        'cannula_size',
        _as_text,
    ),
    'cannulaInsertionDate': (
        'cannula_insertion_date',
        _as_datetime,
    ),
    'urinaryCatheterStatus': (
        'urinary_catheter_status',
        _as_text,
    ),
    'ngTubeStatus': (
        'ng_tube_status',
        _as_text,
    ),
    'drainStatus': (
        'drain_status',
        _as_text,
    ),
    'drainTypeSite': (
        'drain_type_site',
        _as_text,
    ),

    # Notes
    'nursingNotes': (
        'nursing_notes',
        _as_text,
    ),
}


def _map_body_to_vals(body):
    vals = {}

    for js_key, (odoo_field, caster) in _FIELD_MAP.items():
        if js_key in body:
            vals[odoo_field] = caster(body[js_key])

    return vals


def _dt_iso(value):
    if not value:
        return ''

    return value.strftime('%Y-%m-%dT%H:%M')


def _assessment_dict(rec):
    if not rec:
        return None

    return {
        'id': rec.id,
        'admissionRequestId': (
            rec.admission_request_id.id
            if rec.admission_request_id
            else None
        ),
        'patientId': (
            rec.patient_id.id
            if rec.patient_id
            else None
        ),
        'status': rec.status or 'draft',

        # Receiving information
        'receivedById': (
            rec.received_by_id.id
            if rec.received_by_id
            else None
        ),
        'receivedByName': (
            rec.received_by_name
            or rec.received_by_id.name
            or ''
        ),
        'receivingTime': _dt_iso(rec.receiving_time),
        'receivedAt': _dt_iso(rec.received_at),
        'receivingShift': rec.receiving_shift or '',
        'bedConfirmation': rec.bed_confirmation or '',

        # Initial assessment
        'consciousness': rec.consciousness or '',
        'orientation': rec.orientation or '',
        'mobility': rec.mobility or '',
        'generalCondition': rec.general_condition or '',
        'painScore': rec.pain_score or 0,
        'weightKg': rec.weight_kg or 0.0,
        'heightCm': rec.height_cm or 0.0,
        'bmi': rec.bmi or 0.0,
        'requiresIsolation': bool(rec.requires_isolation),
        'oxygenRequired': bool(rec.oxygen_required),
        'npo': bool(rec.npo),
        'highDependency': bool(rec.high_dependency),
        'doctorToBeNotified': bool(
            rec.doctor_to_be_notified
        ),

        # Initial vital signs
        'temperatureC': rec.temperature_c or 0.0,
        'pulseBpm': rec.pulse_bpm or 0,
        'bloodPressure': rec.blood_pressure or '',
        'respiratoryRate': rec.respiratory_rate or 0,
        'spo2Percent': rec.spo2_percent or 0.0,
        'bloodGlucose': rec.blood_glucose or 0.0,
        'vitalPainScore': rec.vital_pain_score or 0,
        'vitalsRecordedByName': (
            rec.vitals_recorded_by_name
            or ''
        ),

        # Allergies
        'drugAllergy': rec.drug_allergy or '',
        'foodAllergy': rec.food_allergy or '',
        'latexAllergy': rec.latex_allergy or '',
        'allergyStatus': rec.allergy_status or '',

        # Infection control
        'isolationType': rec.isolation_type or '',
        'infectionRisk': rec.infection_risk or '',
        'ppeRequired': rec.ppe_required or '',
        'infectionNotes': rec.infection_notes or '',

        # Risk assessment
        'fallRisk': rec.fall_risk or '',
        'bradenScaleScore': rec.braden_scale_score or 0,
        'pressureUlcerRisk': (
            rec.pressure_ulcer_risk
            or ''
        ),
        'nutritionRisk': rec.nutrition_risk or '',
        'psychologicalSafetyRisk': (
            rec.psychological_safety_risk
            or ''
        ),
        'dvtRisk': rec.dvt_risk or '',
        'bleedingRisk': rec.bleeding_risk or '',
        'riskAction': rec.risk_action or '',

        # Belongings
        'belongingMobile': bool(rec.belonging_mobile),
        'belongingMoney': bool(rec.belonging_money),
        'belongingWatch': bool(rec.belonging_watch),
        'belongingClothes': bool(rec.belonging_clothes),
        'belongingDocuments': bool(
            rec.belonging_documents
        ),
        'belongingGlasses': bool(rec.belonging_glasses),
        'belongingDenture': bool(rec.belonging_denture),
        'belongingOther': bool(rec.belonging_other),
        'belongingsHandedTo': (
            rec.belongings_handed_to
            or ''
        ),
        'belongingsRelativeName': (
            rec.belongings_relative_name
            or ''
        ),
        'belongingsSignatureOrId': (
            rec.belongings_signature_or_id
            or ''
        ),

        # IV access / lines / drains
        'cannulaStatus': rec.cannula_status or '',
        'cannulaSite': rec.cannula_site or '',
        'cannulaSize': rec.cannula_size or '',
        'cannulaInsertionDate': _dt_iso(
            rec.cannula_insertion_date
        ),
        'urinaryCatheterStatus': (
            rec.urinary_catheter_status
            or ''
        ),
        'ngTubeStatus': rec.ng_tube_status or '',
        'drainStatus': rec.drain_status or '',
        'drainTypeSite': rec.drain_type_site or '',

        # Notes
        'nursingNotes': rec.nursing_notes or '',

        'createdAt': _dt_iso(rec.create_date),
        'updatedAt': _dt_iso(rec.write_date),
    }


def _current_employee():
    return request.env['hr.employee'].sudo().search(
        [
            ('user_id', '=', request.env.user.id),
        ],
        limit=1,
    )


def _validate_scores(vals):
    for field_name in (
        'pain_score',
        'vital_pain_score',
    ):
        if field_name not in vals:
            continue

        value = vals[field_name]

        if value < 0 or value > 10:
            return 'درجة الألم يجب أن تكون من 0 إلى 10'

    for field_name, label in (
        ('weight_kg', 'الوزن'),
        ('height_cm', 'الطول'),
        ('temperature_c', 'درجة الحرارة'),
        ('pulse_bpm', 'النبض'),
        ('respiratory_rate', 'معدل التنفس'),
        ('spo2_percent', 'تشبع الأكسجين'),
        ('blood_glucose', 'سكر الدم'),
        ('braden_scale_score', 'درجة مقياس برادن'),
    ):
        if field_name not in vals:
            continue

        if vals[field_name] < 0:
            return f'{label} لا يمكن أن يكون قيمة سالبة'

    if (
        'spo2_percent' in vals
        and vals['spo2_percent'] > 100
    ):
        return 'تشبع الأكسجين يجب ألا يتجاوز 100'

    return None


class InpatientNursingController(http.Controller):
    _admission_model = 'saycare.admission.request'
    _assessment_model = (
        'saycare.inpatient.nursing.assessment'
    )

    def _get_admission(self, rec_id):
        return (
            request.env[self._admission_model]
            .sudo()
            .browse(rec_id)
        )

    def _validate_admission(self, admission):
        if not admission.exists():
            return _json(
                {
                    'error': 'حالة الحجز الداخلي غير موجودة',
                },
                404,
            )

        if (
            admission.status != 'admitted'
            or not admission.is_inpatient
        ):
            return _json(
                {
                    'error': (
                        'التقييم التمريضي متاح فقط '
                        'للحالات الداخلية المقبولة'
                    ),
                },
                409,
            )

        return None

    @http.route(
        (
            '/saycare/api/admission-requests/'
            '<int:rec_id>/nursing-assessment'
        ),
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def get_assessment(self, rec_id, **kw):
        admission = self._get_admission(rec_id)

        admission_error = self._validate_admission(
            admission
        )

        if admission_error:
            return admission_error

        assessment = (
            request.env[self._assessment_model]
            .sudo()
            .search(
                [
                    (
                        'admission_request_id',
                        '=',
                        admission.id,
                    ),
                ],
                limit=1,
            )
        )

        return _json(
            {
                'admissionRequest': (
                    _admission_request_dict(admission)
                ),
                'assessment': (
                    _assessment_dict(assessment)
                    if assessment
                    else None
                ),
            }
        )

    @http.route(
        (
            '/saycare/api/admission-requests/'
            '<int:rec_id>/nursing-assessment'
        ),
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def save_assessment(self, rec_id, **kw):
        admission = self._get_admission(rec_id)

        admission_error = self._validate_admission(
            admission
        )

        if admission_error:
            return admission_error

        body, body_error = _load_body()

        if body_error:
            return body_error

        assessment_model = (
            request.env[self._assessment_model]
            .sudo()
        )

        assessment = assessment_model.search(
            [
                (
                    'admission_request_id',
                    '=',
                    admission.id,
                ),
            ],
            limit=1,
        )

        target_status = (
            body.get('status')
            or (
                assessment.status
                if assessment
                else 'draft'
            )
        )

        if target_status not in {
            'draft',
            'received',
        }:
            return _json(
                {
                    'error': 'حالة التقييم غير صحيحة',
                },
                400,
            )

        was_already_received = bool(
            assessment
            and assessment.status == 'received'
        )

        if (
            was_already_received
            and target_status == 'draft'
        ):
            return _json(
                {
                    'error': (
                        'لا يمكن إعادة الحالة المستلمة '
                        'إلى مسودة'
                    ),
                },
                409,
            )

        try:
            vals = _map_body_to_vals(body)

        except (
            TypeError,
            ValueError,
        ):
            return _json(
                {
                    'error': (
                        'توجد قيمة رقمية أو تاريخ '
                        'غير صحيح'
                    ),
                },
                400,
            )

        validation_error = _validate_scores(vals)

        if validation_error:
            return _json(
                {
                    'error': validation_error,
                },
                400,
            )

        vals['status'] = target_status

        if (
            target_status == 'received'
            and not was_already_received
        ):
            employee = _current_employee()

            if employee:
                vals['received_by_id'] = employee.id
                vals['received_by_name'] = (
                    employee.name
                    or request.env.user.name
                    or ''
                )

            else:
                vals['received_by_name'] = (
                    request.env.user.name
                    or ''
                )

            if (
                not assessment
                or not assessment.received_at
            ):
                vals['received_at'] = (
                    fields.Datetime.now()
                )

            if (
                'receiving_time' not in vals
                and (
                    not assessment
                    or not assessment.receiving_time
                )
            ):
                vals['receiving_time'] = (
                    fields.Datetime.now()
                )

        try:
            if assessment:
                assessment.write(vals)

            else:
                vals['admission_request_id'] = (
                    admission.id
                )

                assessment = assessment_model.create(
                    vals
                )

        except Exception:
            request.env.cr.rollback()

            _logger.exception(
                (
                    'Failed to save inpatient nursing '
                    'assessment for admission request %s'
                ),
                admission.id,
            )

            return _json(
                {
                    'error': 'تعذر حفظ التقييم التمريضي',
                },
                500,
            )

        if (
            target_status == 'received'
            and admission.worklist_stage
            != 'received_by_ward'
        ):
            admission.write(
                {
                    'worklist_stage': (
                        'received_by_ward'
                    ),
                }
            )

        return _json(
            {
                'admissionRequest': (
                    _admission_request_dict(admission)
                ),
                'assessment': (
                    _assessment_dict(assessment)
                ),
            }
        )
