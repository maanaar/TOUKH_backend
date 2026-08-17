# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.exceptions import ValidationError
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
            {'error': 'بيانات الطلب غير صحيحة'},
            400,
        )

    if not isinstance(body, dict):
        return None, _json(
            {'error': 'بيانات الطلب يجب أن تكون كائنًا'},
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


def _as_date(value):
    if not value:
        return False

    return fields.Date.to_date(value)


def _as_datetime(value):
    if not value:
        return False

    normalized = str(value).replace('T', ' ')

    if len(normalized) == 16:
        normalized += ':00'

    return fields.Datetime.to_datetime(normalized)


def _field(odoo_name, caster, kind):
    return (odoo_name, caster, kind)


def _text(odoo_name):
    return _field(odoo_name, _as_text, 'text')


def _integer(odoo_name):
    return _field(odoo_name, _as_int, 'int')


def _float(odoo_name):
    return _field(odoo_name, _as_float, 'float')


def _boolean(odoo_name):
    return _field(odoo_name, _as_bool, 'bool')


def _date(odoo_name):
    return _field(odoo_name, _as_date, 'date')


def _datetime(odoo_name):
    return _field(odoo_name, _as_datetime, 'datetime')


_SHEET_CONFIGS = {
    'vital-signs': {
        'model': 'saycare.inpatient.nursing.vital.entry',
        'response_key': 'vitalSigns',
        'required': ('entry_date', 'التاريخ مطلوب'),
        'fields': {
            'date': _date('entry_date'),
            'time': _text('entry_time'),
            'pulse': _integer('pulse'),
            'bloodPressure': _text('blood_pressure'),
            'temperature': _float('temperature'),
            'respiration': _integer('respiration'),
            'score': _integer('score'),
            'notes': _text('notes'),
        },
    },
    'pain': {
        'model': 'saycare.inpatient.nursing.pain.entry',
        'response_key': 'pain',
        'required': ('entry_date', 'تاريخ قياس الألم مطلوب'),
        'fields': {
            'date': _date('entry_date'),
            'age': _integer('age'),
            'time': _text('entry_time'),
            'scaleMethod': _text('scale_method'),
            'painMeasure': _text('pain_measure'),
            'painLocation': _text('pain_location'),
            'painType': _text('pain_type'),
            'interventionType': _text('intervention_type'),
            'nonpharmMethod': _text('nonpharm_method'),
            'nonpharmOtherSpecify': _text(
                'nonpharm_other_specify'
            ),
            'notes': _text('notes'),
        },
    },
    'nurse-observation': {
        'model': 'saycare.inpatient.nursing.observation.entry',
        'response_key': 'nurseObservations',
        'required': ('entry_date', 'التاريخ مطلوب'),
        'fields': {
            'admissionPermitNo': _text(
                'admission_permit_no'
            ),
            'referredFrom': _text('referred_from'),
            'diagnosis': _text('diagnosis'),
            'specialistName': _text('specialist_name'),
            'date': _date('entry_date'),
            'time': _text('entry_time'),
            'note': _text('note'),
        },
    },
    'care-plan': {
        'model': 'saycare.inpatient.nursing.care.plan.entry',
        'response_key': 'carePlans',
        'required': (
            'entry_datetime',
            'الوقت والتاريخ مطلوبان',
        ),
        'fields': {
            'datetime': _datetime('entry_datetime'),
            'nursingDiagnosis': _text(
                'nursing_diagnosis'
            ),
            'patientNeeds': _text('patient_needs'),
            'actions': _text('actions'),
            'expectedOutcomes': _text(
                'expected_outcomes'
            ),
            'timeFrame': _text('time_frame'),
        },
    },
    'once-medication': {
        'model': (
            'saycare.inpatient.nursing.once.medication.entry'
        ),
        'response_key': 'onceMedications',
        'required': (
            'medication_name',
            'اسم الدواء وتركيزه مطلوب',
        ),
        'fields': {
            'doctorName': _text('doctor_name'),
            'diagnosis': _text('diagnosis'),
            'date': _date('entry_date'),
            'time': _text('entry_time'),
            'medicationName': _text('medication_name'),
            'medicationForm': _text('medication_form'),
            'dosage': _text('dosage'),
            'route': _text('route'),
            'instructions': _text('instructions'),
            'pharmacistName': _text('pharmacist_name'),
            'administrationTime': _text(
                'administration_time'
            ),
        },
    },
    'iv-infusion': {
        'model': (
            'saycare.inpatient.nursing.iv.infusion.entry'
        ),
        'response_key': 'ivInfusions',
        'required': (
            'solution_name',
            'اسم المحلول مطلوب',
        ),
        'fields': {
            'prescribedDatetime': _datetime(
                'prescribed_datetime'
            ),
            'solutionName': _text('solution_name'),
            'volume': _float('volume'),
            'additives': _text('additives'),
            'rate': _text('rate'),
            'line': _text('line'),
            'instructions': _text('instructions'),
            'doctorName': _text('doctor_name'),
            'pharmacistName': _text('pharmacist_name'),
            'administeredDatetime': _datetime(
                'administered_datetime'
            ),
            'administeredVolume': _float(
                'administered_volume'
            ),
        },
    },
    'fluid-balance': {
        'model': (
            'saycare.inpatient.nursing.fluid.balance.entry'
        ),
        'response_key': 'fluidBalance',
        'required': (
            'entry_datetime',
            'تاريخ ووقت التسجيل مطلوبان',
        ),
        'fields': {
            'diagnosis': _text('diagnosis'),
            'entryDatetime': _datetime('entry_datetime'),
            'oralIntake': _float('oral_intake'),
            'ivIntake': _float('iv_intake'),
            'urineOutput': _float('urine_output'),
            'drainOutput': _float('drain_output'),
        },
        'readonly': {
            'totalIntake': ('total_intake', 'float'),
            'totalOutput': ('total_output', 'float'),
            'balance': ('balance', 'float'),
        },
    },
    'blood-glucose': {
        'model': 'saycare.inpatient.nursing.glucose.entry',
        'response_key': 'bloodGlucose',
        'required': (
            'entry_date',
            'تاريخ قياس السكر مطلوب',
        ),
        'fields': {
            'diagnosis': _text('diagnosis'),
            'date': _date('entry_date'),
            'time': _text('entry_time'),
            'level': _float('level'),
            'oral': _boolean('oral'),
            'insulinType': _text('insulin_type'),
            'doseUnits': _float('dose_units'),
            'route': _text('route'),
            'site': _text('site'),
            'urineAcetone': _text('urine_acetone'),
            'notes': _text('notes'),
        },
    },
    'icu-lab': {
        'model': 'saycare.inpatient.nursing.icu.lab.entry',
        'response_key': 'icuLabs',
        'required': (
            'entry_date',
            'تاريخ نتائج المعمل مطلوب',
        ),
        'fields': {
            'date': _date('entry_date'),
            'wbc': _float('wbc'),
            'rbc': _float('rbc'),
            'hb': _float('hb'),
            'hct': _float('hct'),
            'platelets': _float('platelets'),
            'pt': _float('pt'),
            'pc': _float('pc'),
            'inr': _float('inr'),
            'ptt': _float('ptt'),
            'totalProtein': _float('total_protein'),
            'albumin': _float('albumin'),
            'tBilirubin': _float('t_bilirubin'),
            'dBilirubin': _float('d_bilirubin'),
            'altSgpt': _float('alt_sgpt'),
            'astSgot': _float('ast_sgot'),
            'alp': _float('alp'),
            'urea': _float('urea'),
            'creatinine': _float('creatinine'),
            'uricAcid': _float('uric_acid'),
            'na': _float('na'),
            'k': _float('k'),
            'ca': _float('ca'),
            'mg': _float('mg'),
            'po4': _float('po4'),
            'cpk': _float('cpk'),
            'cpkMb': _float('cpk_mb'),
            'ldh': _float('ldh'),
            'troponin': _float('troponin'),
            'cholesterol': _float('cholesterol'),
            'triglycerides': _float('triglycerides'),
            'ldl': _float('ldl'),
            'hdl': _float('hdl'),
            'ph': _float('ph'),
            'pco2': _float('pco2'),
            'o2Sat': _float('o2_sat'),
            'hco3': _float('hco3'),
            'otherNotes': _text('other_notes'),
        },
    },
    'pressure-ulcer': {
        'model': (
            'saycare.inpatient.nursing.pressure.ulcer.entry'
        ),
        'response_key': 'pressureUlcers',
        'required': (
            'discovery_date',
            'تاريخ اكتشاف القرحة مطلوب',
        ),
        'fields': {
            'discoveryDate': _date('discovery_date'),
            'location': _text('location'),
            'grade': _text('grade'),
            'position': _text('position'),
            'turningChartPlaced': _boolean(
                'turning_chart_placed'
            ),
            'pressureAvoided': _boolean(
                'pressure_avoided'
            ),
            'areaCleanDry': _boolean('area_clean_dry'),
            'airMattress': _boolean('air_mattress'),
            'woundCleanedSaline': _boolean(
                'wound_cleaned_saline'
            ),
            'antibioticUsed': _boolean(
                'antibiotic_used'
            ),
            'sterileGauzeChanged': _boolean(
                'sterile_gauze_changed'
            ),
            'colorNotes': _text('color_notes'),
            'dischargeType': _text('discharge_type'),
            'infectionSignsReported': _boolean(
                'infection_signs_reported'
            ),
            'carePlan': _text('care_plan'),
            'repositioningEducation': _boolean(
                'repositioning_education'
            ),
        },
    },
    'physical-restraint': {
        'model': (
            'saycare.inpatient.nursing.physical.restraint.entry'
        ),
        'response_key': 'physicalRestraint',
        'required': (
            'follow_up_time',
            'وقت المتابعة مطلوب',
        ),
        'fields': {
            'department': _text('department'),
            'admissionDate': _date('admission_date'),
            'diagnosis': _text('diagnosis'),
            'restraintType': _text('restraint_type'),
            'chemicalGiven': _text('chemical_given'),
            'restraintLocationHand': _text(
                'restraint_location_hand'
            ),
            'restraintLocationFoot': _text(
                'restraint_location_foot'
            ),
            'restraintBody': _boolean('restraint_body'),
            'durationType': _text('duration_type'),
            'durationOther': _text('duration_other'),
            'releaseFrequency': _text('release_frequency'),
            'releaseMinutes': _integer('release_minutes'),
            'physicianEvaluated': _boolean(
                'physician_evaluated'
            ),
            'physicianSign': _text('physician_sign'),
            'physicianTime': _text('physician_time'),
            'physicianDate': _date('physician_date'),
            'followUpTime': _text('follow_up_time'),
            'followUpNotes': _text('follow_up_notes'),
            'followUpSign': _text('follow_up_sign'),
        },
    },
    'vae-surveillance': {
        'model': (
            'saycare.inpatient.nursing.vae.surveillance.entry'
        ),
        'response_key': 'vaeSurveillance',
        'required': (
            'entry_date',
            'تاريخ اليوم مطلوب',
        ),
        'fields': {
            'diagnosis': _text('diagnosis'),
            'admissionDate': _date('admission_date'),
            'ventilatorConnectionDate': _date(
                'ventilator_connection_date'
            ),
            'calendarDay': _date('entry_date'),
            'ventDay': _integer('vent_day'),
            'peep10am': _float('peep_10am'),
            'fio210am': _float('fio2_10am'),
            'peep2pm': _float('peep_2pm'),
            'fio22pm': _float('fio2_2pm'),
            'peep6pm': _float('peep_6pm'),
            'fio26pm': _float('fio2_6pm'),
            'peep10pm': _float('peep_10pm'),
            'fio210pm': _float('fio2_10pm'),
            'peep2am': _float('peep_2am'),
            'fio22am': _float('fio2_2am'),
            'peep6am': _float('peep_6am'),
            'fio26am': _float('fio2_6am'),
            'dailyMin': _float('daily_min'),
            'sedationVacationDone': _boolean(
                'sedation_vacation_done'
            ),
            'weaningTrialDone': _boolean(
                'weaning_trial_done'
            ),
            'notes': _text('notes'),
        },
    },
    'quality-turning-chart': {
        'model': (
            'saycare.inpatient.nursing.quality.turning.chart.entry'
        ),
        'response_key': 'qualityManagement',
        'required': (
            'entry_date',
            'التاريخ مطلوب',
        ),
        'fields': {
            'department': _text('department'),
            'admissionDate': _date('admission_date'),
            'initialUlcerPresent': _text(
                'initial_ulcer_present'
            ),
            'initialUlcerLocation': _text(
                'initial_ulcer_location'
            ),
            'initialUlcerGrade': _text(
                'initial_ulcer_grade'
            ),
            'entryDate': _date('entry_date'),
            'position8am': _text('position_8am'),
            'position10am': _text('position_10am'),
            'position12pm': _text('position_12pm'),
            'position2pm': _text('position_2pm'),
            'position4pm': _text('position_4pm'),
            'position6pm': _text('position_6pm'),
            'position8pm': _text('position_8pm'),
            'position10pm': _text('position_10pm'),
            'position12am': _text('position_12am'),
            'position2am': _text('position_2am'),
            'position4am': _text('position_4am'),
            'position6am': _text('position_6am'),
            'nurseSign': _text('nurse_sign'),
            'notes': _text('notes'),
        },
    },
}


def _dt_iso(value):
    if not value:
        return ''

    return value.strftime('%Y-%m-%dT%H:%M')


def _date_iso(value):
    if not value:
        return ''

    return value.isoformat()


def _serialize_value(value, kind):
    if kind == 'datetime':
        return _dt_iso(value)

    if kind == 'date':
        return _date_iso(value)

    if kind == 'bool':
        return bool(value)

    if kind == 'int':
        return value or 0

    if kind == 'float':
        return value or 0.0

    return value or ''


def _map_body_to_vals(body, config):
    vals = {}

    for js_key, (
        odoo_field,
        caster,
        _kind,
    ) in config['fields'].items():
        if js_key in body:
            vals[odoo_field] = caster(body[js_key])

    return vals


def _entry_dict(record, config):
    result = {
        'id': record.id,
        'admissionRequestId': (
            record.admission_request_id.id
            if record.admission_request_id
            else None
        ),
        'patientId': (
            record.patient_id.id
            if record.patient_id
            else None
        ),
        'recordedById': (
            record.recorded_by_id.id
            if record.recorded_by_id
            else None
        ),
        'recordedByName': (
            record.recorded_by_name
            or record.recorded_by_id.name
            or ''
        ),
        'recordedAt': _dt_iso(record.recorded_at),
        'createdAt': _dt_iso(record.create_date),
        'updatedAt': _dt_iso(record.write_date),
    }

    for js_key, (
        odoo_field,
        _caster,
        kind,
    ) in config['fields'].items():
        result[js_key] = _serialize_value(
            record[odoo_field],
            kind,
        )

    for js_key, (
        odoo_field,
        kind,
    ) in config.get('readonly', {}).items():
        result[js_key] = _serialize_value(
            record[odoo_field],
            kind,
        )

    return result


def _current_employee():
    return request.env['hr.employee'].sudo().search(
        [('user_id', '=', request.env.user.id)],
        limit=1,
    )


def _get_config(sheet_type):
    return _SHEET_CONFIGS.get(sheet_type)


def _required_error(config, vals, record=None):
    field_name, message = config['required']

    if field_name in vals:
        value = vals[field_name]
    elif record:
        value = record[field_name]
    else:
        value = False

    if value in (None, '', False):
        return message

    return None


def _validate_ranges(sheet_type, vals):
    range_rules = {
        'vital-signs': [
            ('pulse', 0, None, 'النبض'),
            ('temperature', 0, None, 'درجة الحرارة'),
            ('respiration', 0, None, 'التنفس'),
            ('score', 0, None, 'الدرجة'),
        ],
        'pain': [
            ('age', 0, None, 'السن'),
        ],
        'iv-infusion': [
            ('volume', 0, None, 'حجم المحلول'),
            (
                'administered_volume',
                0,
                None,
                'الحجم المعطى',
            ),
        ],
        'fluid-balance': [
            ('oral_intake', 0, None, 'السوائل بالفم'),
            ('iv_intake', 0, None, 'السوائل بالوريد'),
            ('urine_output', 0, None, 'البول'),
            ('drain_output', 0, None, 'الدرنقة'),
        ],
        'blood-glucose': [
            ('level', 0, None, 'نسبة سكر الدم'),
            ('dose_units', 0, None, 'الجرعة'),
        ],
        'icu-lab': [
            ('ph', 0, 14, 'pH'),
            ('o2_sat', 0, 100, 'O2 Sat'),
        ],
        'vae-surveillance': [
            ('vent_day', 0, None, 'يوم جهاز التنفس الاصطناعي'),
            ('peep_10am', 0, None, 'PEEP - 10 صباحاً'),
            ('fio2_10am', 0, 100, 'FiO2 - 10 صباحاً'),
            ('peep_2pm', 0, None, 'PEEP - 2 ظهراً'),
            ('fio2_2pm', 0, 100, 'FiO2 - 2 ظهراً'),
            ('peep_6pm', 0, None, 'PEEP - 6 مساءً'),
            ('fio2_6pm', 0, 100, 'FiO2 - 6 مساءً'),
            ('peep_10pm', 0, None, 'PEEP - 10 مساءً'),
            ('fio2_10pm', 0, 100, 'FiO2 - 10 مساءً'),
            ('peep_2am', 0, None, 'PEEP - 2 صباحاً'),
            ('fio2_2am', 0, 100, 'FiO2 - 2 صباحاً'),
            ('peep_6am', 0, None, 'PEEP - 6 صباحاً'),
            ('fio2_6am', 0, 100, 'FiO2 - 6 صباحاً'),
            ('daily_min', 0, None, 'الحد الأدنى اليومي'),
        ],
    }

    for (
        field_name,
        minimum,
        maximum,
        label,
    ) in range_rules.get(sheet_type, []):
        if field_name not in vals:
            continue

        value = vals[field_name]

        if minimum is not None and value < minimum:
            return f'{label} لا يمكن أن يكون أقل من {minimum}'

        if maximum is not None and value > maximum:
            return f'{label} لا يمكن أن يتجاوز {maximum}'

    return None


class InpatientNursingSheetsController(http.Controller):
    _admission_model = 'saycare.admission.request'

    def _get_admission(self, record_id):
        return (
            request.env[self._admission_model]
            .sudo()
            .browse(record_id)
        )

    def _validate_admission(self, admission):
        if not admission.exists():
            return _json(
                {'error': 'حالة الحجز الداخلي غير موجودة'},
                404,
            )

        if (
            admission.status != 'admitted'
            or not admission.is_inpatient
        ):
            return _json(
                {
                    'error': (
                        'النماذج التمريضية متاحة فقط '
                        'للحالات الداخلية المقبولة'
                    ),
                },
                409,
            )

        return None

    @http.route(
        (
            '/saycare/api/admission-requests/'
            '<int:record_id>/nursing-sheets'
        ),
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def get_sheets(self, record_id, **kwargs):
        admission = self._get_admission(record_id)
        admission_error = self._validate_admission(
            admission
        )

        if admission_error:
            return admission_error

        sheets = {}

        for config in _SHEET_CONFIGS.values():
            records = (
                request.env[config['model']]
                .sudo()
                .search(
                    [
                        (
                            'admission_request_id',
                            '=',
                            admission.id,
                        ),
                    ]
                )
            )

            sheets[config['response_key']] = [
                _entry_dict(record, config)
                for record in records
            ]

        return _json(
            {
                'admissionRequest': (
                    _admission_request_dict(admission)
                ),
                'sheets': sheets,
            }
        )

    @http.route(
        (
            '/saycare/api/admission-requests/'
            '<int:record_id>/nursing-sheets/'
            '<string:sheet_type>'
        ),
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def create_entry(
        self,
        record_id,
        sheet_type,
        **kwargs,
    ):
        config = _get_config(sheet_type)

        if not config:
            return _json(
                {'error': 'نوع النموذج التمريضي غير صحيح'},
                404,
            )

        admission = self._get_admission(record_id)
        admission_error = self._validate_admission(
            admission
        )

        if admission_error:
            return admission_error

        body, body_error = _load_body()

        if body_error:
            return body_error

        try:
            vals = _map_body_to_vals(body, config)
        except (TypeError, ValueError):
            return _json(
                {
                    'error': (
                        'توجد قيمة رقمية أو تاريخ '
                        'غير صحيح'
                    ),
                },
                400,
            )

        required_error = _required_error(config, vals)

        if required_error:
            return _json({'error': required_error}, 400)

        range_error = _validate_ranges(
            sheet_type,
            vals,
        )

        if range_error:
            return _json({'error': range_error}, 400)

        employee = _current_employee()

        vals.update({
            'admission_request_id': admission.id,
            'recorded_by_id': (
                employee.id
                if employee
                else False
            ),
            'recorded_by_name': (
                (employee.name if employee else '')
                or request.env.user.name
                or ''
            ),
            'recorded_at': fields.Datetime.now(),
        })

        try:
            record = (
                request.env[config['model']]
                .sudo()
                .create(vals)
            )
        except ValidationError as error:
            request.env.cr.rollback()
            return _json(
                {'error': str(error)},
                400,
            )
        except (TypeError, ValueError):
            request.env.cr.rollback()
            return _json(
                {'error': 'توجد قيمة غير صحيحة في النموذج'},
                400,
            )
        except Exception:
            request.env.cr.rollback()
            _logger.exception(
                (
                    'Failed to create inpatient nursing '
                    'sheet entry %s for admission %s'
                ),
                sheet_type,
                admission.id,
            )
            return _json(
                {'error': 'تعذر حفظ النموذج التمريضي'},
                500,
            )

        return _json(
            {
                'sheetType': sheet_type,
                'entry': _entry_dict(record, config),
            },
            201,
        )

    @http.route(
        (
            '/saycare/api/nursing-sheet-entries/'
            '<string:sheet_type>/<int:entry_id>'
        ),
        type='http',
        auth='user',
        methods=['PUT'],
        csrf=False,
    )
    def update_entry(
        self,
        sheet_type,
        entry_id,
        **kwargs,
    ):
        config = _get_config(sheet_type)

        if not config:
            return _json(
                {'error': 'نوع النموذج التمريضي غير صحيح'},
                404,
            )

        record = (
            request.env[config['model']]
            .sudo()
            .browse(entry_id)
        )

        if not record.exists():
            return _json(
                {'error': 'سجل النموذج التمريضي غير موجود'},
                404,
            )

        admission = record.admission_request_id
        admission_error = self._validate_admission(
            admission
        )

        if admission_error:
            return admission_error

        body, body_error = _load_body()

        if body_error:
            return body_error

        try:
            vals = _map_body_to_vals(body, config)
        except (TypeError, ValueError):
            return _json(
                {
                    'error': (
                        'توجد قيمة رقمية أو تاريخ '
                        'غير صحيح'
                    ),
                },
                400,
            )

        if not vals:
            return _json(
                {'error': 'لا توجد بيانات لتحديثها'},
                400,
            )

        required_error = _required_error(
            config,
            vals,
            record,
        )

        if required_error:
            return _json({'error': required_error}, 400)

        range_error = _validate_ranges(
            sheet_type,
            vals,
        )

        if range_error:
            return _json({'error': range_error}, 400)

        try:
            record.write(vals)
        except ValidationError as error:
            request.env.cr.rollback()
            return _json(
                {'error': str(error)},
                400,
            )
        except (TypeError, ValueError):
            request.env.cr.rollback()
            return _json(
                {'error': 'توجد قيمة غير صحيحة في النموذج'},
                400,
            )
        except Exception:
            request.env.cr.rollback()
            _logger.exception(
                (
                    'Failed to update inpatient nursing '
                    'sheet entry %s/%s'
                ),
                sheet_type,
                entry_id,
            )
            return _json(
                {'error': 'تعذر تحديث النموذج التمريضي'},
                500,
            )

        return _json(
            {
                'sheetType': sheet_type,
                'entry': _entry_dict(record, config),
            }
        )
