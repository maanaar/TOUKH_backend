# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

from .admission_requests import _admission_request_dict
from .inpatient_nursing_sheets import (
    _date,
    _datetime,
    _entry_dict,
    _float,
    _integer,
    _map_body_to_vals,
    _required_error,
    _text,
)
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


_SHEET_CONFIGS = {
    'vital-signs': {
        'model': 'saycare.critical.care.vital.entry',
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
    'care-plan': {
        'model': 'saycare.critical.care.nursing.plan.entry',
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
    'treatment': {
        'model': 'saycare.critical.care.treatment.entry',
        'response_key': 'treatments',
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
        'model': 'saycare.critical.care.iv.infusion.entry',
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
    'icu-lab': {
        'model': 'saycare.critical.care.icu.lab.entry',
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
}


def _current_employee():
    return request.env['hr.employee'].sudo().search(
        [('user_id', '=', request.env.user.id)],
        limit=1,
    )


def _get_config(sheet_type):
    return _SHEET_CONFIGS.get(sheet_type)


def _validate_ranges(sheet_type, vals):
    range_rules = {
        'vital-signs': [
            ('pulse', 0, None, 'النبض'),
            ('temperature', 0, None, 'درجة الحرارة'),
            ('respiration', 0, None, 'التنفس'),
            ('score', 0, None, 'الدرجة'),
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
        'icu-lab': [
            ('ph', 0, 14, 'pH'),
            ('o2_sat', 0, 100, 'O2 Sat'),
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


class CriticalCareSheetsController(http.Controller):
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

        return None

    @http.route(
        (
            '/saycare/api/admission-requests/'
            '<int:record_id>/critical-care-sheets'
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
            '<int:record_id>/critical-care-sheets/'
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
                {'error': 'نوع نموذج الرعاية الحرجة غير صحيح'},
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
                    'Failed to create critical care '
                    'sheet entry %s for admission %s'
                ),
                sheet_type,
                admission.id,
            )
            return _json(
                {'error': 'تعذر حفظ نموذج الرعاية الحرجة'},
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
            '/saycare/api/critical-care-sheet-entries/'
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
                {'error': 'نوع نموذج الرعاية الحرجة غير صحيح'},
                404,
            )

        record = (
            request.env[config['model']]
            .sudo()
            .browse(entry_id)
        )

        if not record.exists():
            return _json(
                {'error': 'سجل نموذج الرعاية الحرجة غير موجود'},
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
                    'Failed to update critical care '
                    'sheet entry %s/%s'
                ),
                sheet_type,
                entry_id,
            )
            return _json(
                {'error': 'تعذر تحديث نموذج الرعاية الحرجة'},
                500,
            )

        return _json(
            {
                'sheetType': sheet_type,
                'entry': _entry_dict(record, config),
            }
        )
