# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from .utils import _json


_logger = logging.getLogger(__name__)


def _load_body():
    try:
        return json.loads(request.httprequest.data or "{}"), None
    except json.JSONDecodeError:
        return None, _json({"error": "invalid JSON"}, 400)


def _int_or_false(value):
    try:
        return int(value) if value not in (None, "", False) else False
    except (TypeError, ValueError):
        return False


def _text_value(value):
    return str(value or "")


def _bool_value(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _datetime_value(value):
    if not value:
        return False
    value = str(value).replace("T", " ")
    if len(value) == 16:
        value += ":00"
    try:
        return fields.Datetime.to_datetime(value)
    except (TypeError, ValueError):
        raise ValidationError("invalid datetime value")


def _belonging_commands(items):
    commands = [(5, 0, 0)]
    for item in items or []:
        item_name = (item.get("itemName") or "").strip()
        if not item_name:
            raise ValidationError("belonging item name is required")
        quantity = _int_or_false(item.get("quantity")) or 1
        if quantity <= 0:
            raise ValidationError("belonging quantity must be greater than zero")
        commands.append(
            (
                0,
                0,
                {
                    "category": item.get("category") or "other",
                    "item_name": item_name,
                    "description": item.get("description") or "",
                    "quantity": quantity,
                    "condition": item.get("condition") or "",
                    "sealed_container_no": item.get("sealedContainerNo") or "",
                    "storage_location": item.get("storageLocation") or "",
                    "notes": item.get("notes") or "",
                },
            )
        )
    return commands


_FIELD_MAP = {
    "caseNo": ("case_no", _text_value),
    "sourceType": ("source_type", _text_value),
    "patientId": ("patient_id", _int_or_false),
    "admissionRequestId": ("admission_request_id", _int_or_false),
    "deceasedName": ("deceased_name", _text_value),
    "patientMrn": ("patient_mrn", _text_value),
    "medicalFileNumber": ("medical_file_number", _text_value),
    "entryPermitNo": ("entry_permit_no", _text_value),
    "idType": ("id_type", _text_value),
    "idNumber": ("id_number", _text_value),
    "gender": ("gender", _text_value),
    "dateOfBirth": ("date_of_birth", lambda value: value or False),
    "age": ("age", lambda value: _int_or_false(value) or 0),
    "nationality": ("nationality", _text_value),
    "unknownIdentity": ("unknown_identity", _bool_value),
    "identificationNotes": ("identification_notes", _text_value),
    "deathDateTime": ("death_datetime", _datetime_value),
    "deathPlace": ("death_place", _text_value),
    "deathPlaceNotes": ("death_place_notes", _text_value),
    "departmentId": ("department_id", _int_or_false),
    "attendingDoctorId": ("attending_doctor_id", _int_or_false),
    "attendingDoctorName": ("attending_doctor_name", _text_value),
    "causeOfDeath": ("cause_of_death", _text_value),
    "deathType": ("death_type", _text_value),
    "prosecutionCase": ("prosecution_case", _bool_value),
    "prosecutionAuthority": ("prosecution_authority", _text_value),
    "policeReportNo": ("police_report_no", _text_value),
    "prosecutionCaseNo": ("prosecution_case_no", _text_value),
    "prosecutionPermitDateTime": (
        "prosecution_permit_datetime",
        _datetime_value,
    ),
    "prosecutionNotes": ("prosecution_notes", _text_value),
    "receivingSource": ("receiving_source", _text_value),
    "referringEntity": ("referring_entity", _text_value),
    "referringReference": ("referring_reference", _text_value),
    "deliveredByName": ("delivered_by_name", _text_value),
    "deliveredByRole": ("delivered_by_role", _text_value),
    "deliveredByIdNumber": ("delivered_by_id_number", _text_value),
    "deliveredByPhone": ("delivered_by_phone", _text_value),
    "ambulanceNumber": ("ambulance_number", _text_value),
    "receptionDateTime": ("reception_datetime", _datetime_value),
    "receivedById": ("received_by_id", _int_or_false),
    "belongingsStatus": ("belongings_status", _text_value),
    "notes": ("notes", _text_value),
}


def _vals_from_body(body, include_belongings=True):
    vals = {}
    for body_key, (field_name, caster) in _FIELD_MAP.items():
        if body_key in body:
            vals[field_name] = caster(body[body_key])
    if include_belongings and "belongings" in body:
        vals["belonging_ids"] = _belonging_commands(body.get("belongings"))
    return vals


def _belonging_dict(record):
    return {
        "id": record.id,
        "category": record.category or "",
        "itemName": record.item_name or "",
        "description": record.description or "",
        "quantity": record.quantity,
        "condition": record.condition or "",
        "sealedContainerNo": record.sealed_container_no or "",
        "storageLocation": record.storage_location or "",
        "status": record.status or "",
        "receivedById": record.received_by_id.id if record.received_by_id else None,
        "receivedByName": record.received_by_id.name if record.received_by_id else "",
        "receivedAt": fields.Datetime.to_string(record.received_at)
        if record.received_at
        else "",
        "notes": record.notes or "",
    }


def _case_dict(record, detail=False):
    data = {
        "id": record.id,
        "caseNo": record.case_no or "",
        "state": record.state or "",
        "sourceType": record.source_type or "",
        "patientId": record.patient_id.id if record.patient_id else None,
        "admissionRequestId": record.admission_request_id.id
        if record.admission_request_id
        else None,
        "deceasedName": record.deceased_name or "",
        "patientMrn": record.patient_mrn or "",
        "medicalFileNumber": record.medical_file_number or "",
        "entryPermitNo": record.entry_permit_no or "",
        "idType": record.id_type or "",
        "idNumber": record.id_number or "",
        "gender": record.gender or "",
        "dateOfBirth": record.date_of_birth.isoformat()
        if record.date_of_birth
        else "",
        "age": record.age,
        "nationality": record.nationality or "",
        "unknownIdentity": bool(record.unknown_identity),
        "identificationNotes": record.identification_notes or "",
        "deathDateTime": fields.Datetime.to_string(record.death_datetime)
        if record.death_datetime
        else "",
        "deathPlace": record.death_place or "",
        "deathPlaceNotes": record.death_place_notes or "",
        "departmentId": record.department_id.id if record.department_id else None,
        "departmentName": record.department_id.display_name
        if record.department_id
        else "",
        "attendingDoctorId": record.attending_doctor_id.id
        if record.attending_doctor_id
        else None,
        "attendingDoctorName": record.attending_doctor_id.name
        if record.attending_doctor_id
        else (record.attending_doctor_name or ""),
        "causeOfDeath": record.cause_of_death or "",
        "deathType": record.death_type or "",
        "prosecutionCase": bool(record.prosecution_case),
        "prosecutionAuthority": record.prosecution_authority or "",
        "policeReportNo": record.police_report_no or "",
        "prosecutionCaseNo": record.prosecution_case_no or "",
        "prosecutionPermitDateTime": fields.Datetime.to_string(
            record.prosecution_permit_datetime
        )
        if record.prosecution_permit_datetime
        else "",
        "prosecutionNotes": record.prosecution_notes or "",
        "receivingSource": record.receiving_source or "",
        "referringEntity": record.referring_entity or "",
        "referringReference": record.referring_reference or "",
        "deliveredByName": record.delivered_by_name or "",
        "deliveredByRole": record.delivered_by_role or "",
        "deliveredByIdNumber": record.delivered_by_id_number or "",
        "deliveredByPhone": record.delivered_by_phone or "",
        "ambulanceNumber": record.ambulance_number or "",
        "receptionDateTime": fields.Datetime.to_string(record.reception_datetime)
        if record.reception_datetime
        else "",
        "receivedById": record.received_by_id.id if record.received_by_id else None,
        "receivedByName": record.received_by_id.name if record.received_by_id else "",
        "fridgeId": record.fridge_id.id if record.fridge_id else None,
        "fridgeName": record.fridge_id.name if record.fridge_id else "",
        "drawerId": record.drawer_id.id if record.drawer_id else None,
        "drawerName": (f"{record.fridge_id.code} / {record.drawer_id.name or record.drawer_id.code}" if record.drawer_id and record.fridge_id else ""),
        "belongingsStatus": record.belongings_status or "",
        "notes": record.notes or "",
        "confirmedById": record.confirmed_by_id.id
        if record.confirmed_by_id
        else None,
        "confirmedByName": record.confirmed_by_id.name
        if record.confirmed_by_id
        else "",
        "confirmedAt": fields.Datetime.to_string(record.confirmed_at)
        if record.confirmed_at
        else "",
        "createdAt": fields.Datetime.to_string(record.create_date)
        if record.create_date
        else "",
        "updatedAt": fields.Datetime.to_string(record.write_date)
        if record.write_date
        else "",
    }
    if detail:
        data["belongings"] = [
            _belonging_dict(item) for item in record.belonging_ids
        ]
    return data


class MortuaryReceptionController(http.Controller):
    _case_model = "saycare.mortuary.case"

    @http.route(
        "/api/v1/mortuary/cases",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_cases(
        self,
        q="",
        state="",
        source_type="",
        prosecution="",
        unknown="",
        date_from="",
        date_to="",
        limit=50,
        offset=0,
        **kw,
    ):
        domain = []
        q = (q or "").strip()
        if q:
            domain += [
                "|",
                "|",
                "|",
                "|",
                "|",
                ("case_no", "ilike", q),
                ("deceased_name", "ilike", q),
                ("id_number", "ilike", q),
                ("patient_mrn", "ilike", q),
                ("police_report_no", "ilike", q),
                ("referring_reference", "ilike", q),
            ]
        if state:
            domain.append(("state", "=", state))
        if source_type:
            domain.append(("source_type", "=", source_type))
        if prosecution not in ("", None):
            domain.append(("prosecution_case", "=", _bool_value(prosecution)))
        if unknown not in ("", None):
            domain.append(("unknown_identity", "=", _bool_value(unknown)))
        if date_from:
            domain.append(("reception_datetime", ">=", f"{date_from} 00:00:00"))
        if date_to:
            domain.append(("reception_datetime", "<=", f"{date_to} 23:59:59"))

        try:
            limit = max(1, min(int(limit), 200))
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            limit, offset = 50, 0

        model = request.env[self._case_model].sudo()
        total = model.search_count(domain)
        records = model.search(
            domain,
            order="reception_datetime desc, id desc",
            limit=limit,
            offset=offset,
        )
        return _json(
            {
                "total": total,
                "limit": limit,
                "offset": offset,
                "cases": [_case_dict(record) for record in records],
            }
        )

    @http.route(
        "/api/v1/mortuary/cases/<int:case_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def get_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "mortuary case not found"}, 404)
        return _json(_case_dict(record, detail=True))

    @http.route(
        "/api/v1/mortuary/cases",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def create_case(self, **kw):
        body, error = _load_body()
        if error:
            return error

        case_no = " ".join((body.get("caseNo") or "").strip().split())
        if not case_no:
            return _json({"error": "mortuary case number is required"}, 400)

        model = request.env[self._case_model].sudo()
        if model.search_count([("case_no", "=", case_no)]):
            return _json({"error": "mortuary case number already exists"}, 409)

        try:
            record = model.create(_vals_from_body(body))
            return _json(_case_dict(record, detail=True), 201)
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("mortuary case creation failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/mortuary/cases/<int:case_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "mortuary case not found"}, 404)
        if record.state != "draft":
            return _json(
                {"error": "only draft mortuary cases can be edited"},
                409,
            )

        body, error = _load_body()
        if error:
            return error

        if "caseNo" in body:
            case_no = " ".join((body.get("caseNo") or "").strip().split())
            duplicate = request.env[self._case_model].sudo().search_count(
                [("case_no", "=", case_no), ("id", "!=", record.id)]
            )
            if duplicate:
                return _json({"error": "mortuary case number already exists"}, 409)

        try:
            record.write(_vals_from_body(body))
            return _json(_case_dict(record, detail=True))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("mortuary case update failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/mortuary/cases/<int:case_id>/confirm",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def confirm_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "mortuary case not found"}, 404)

        body, error = _load_body()
        if error:
            return error

        try:
            record.action_confirm_storage(body.get("drawerId"))
            return _json(_case_dict(record, detail=True))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            message = str(exc)
            code = 409 if "occupied" in message.lower() else 400
            return _json({"error": message}, code)
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("mortuary case confirmation failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/mortuary/cases/<int:case_id>/cancel",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def cancel_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "mortuary case not found"}, 404)
        try:
            record.action_cancel_draft()
            return _json(_case_dict(record, detail=True))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/mortuary/fridges",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_fridges(self, available_only="1", **kw):
        only_available = _bool_value(available_only)
        fridges = request.env["saycare.mortuary.fridge"].sudo().search(
            [("active", "=", True)],
            order="code asc",
        )
        result = []
        for fridge in fridges:
            drawers = fridge.drawer_ids.filtered(
                lambda drawer: drawer.active
                and (not only_available or not drawer.current_case_id)
            )
            result.append(
                {
                    "id": fridge.id,
                    "code": fridge.code or "",
                    "name": fridge.name or "",
                    "location": fridge.location or "",
                    "availableDrawerCount": len(
                        drawers.filtered(lambda drawer: not drawer.current_case_id)
                    ),
                    "drawers": [
                        {
                            "id": drawer.id,
                            "code": drawer.code or "",
                            "name": drawer.name or drawer.code or "",
                            "displayName": f"{fridge.code} / {drawer.name or drawer.code}",
                            "occupied": bool(drawer.current_case_id),
                            "currentCaseId": drawer.current_case_id.id
                            if drawer.current_case_id
                            else None,
                            "currentCaseNo": drawer.current_case_id.case_no
                            if drawer.current_case_id
                            else "",
                        }
                        for drawer in drawers
                    ],
                }
            )
        return _json({"fridges": result})
