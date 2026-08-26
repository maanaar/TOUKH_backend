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


class MorgueReceptionController(http.Controller):
    _case_model = "saycare.morgue.case"

    @http.route(
        "/api/v1/morgue/cases",
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
        "/api/v1/morgue/cases/<int:case_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def get_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "morgue case not found"}, 404)
        return _json(_case_dict(record, detail=True))

    @http.route(
        "/api/v1/morgue/cases",
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
            return _json({"error": "morgue case number is required"}, 400)

        model = request.env[self._case_model].sudo()
        if model.search_count([("case_no", "=", case_no)]):
            return _json({"error": "رقم الحالة مستخدم بالفعل."}, 409)

        try:
            record = model.create(_vals_from_body(body))
            return _json(_case_dict(record, detail=True), 201)
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("morgue case creation failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "morgue case not found"}, 404)
        if record.state != "draft":
            return _json(
                {"error": "only draft morgue cases can be edited"},
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
                return _json({"error": "رقم الحالة مستخدم بالفعل."}, 409)

        try:
            record.write(_vals_from_body(body))
            return _json(_case_dict(record, detail=True))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)
        except Exception as exc:
            request.env.cr.rollback()
            _logger.exception("morgue case update failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/confirm",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def confirm_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "morgue case not found"}, 404)

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
            _logger.exception("morgue case confirmation failed")
            return _json({"error": str(exc)}, 500)

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/cancel",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def cancel_case(self, case_id, **kw):
        record = request.env[self._case_model].sudo().browse(case_id)
        if not record.exists():
            return _json({"error": "morgue case not found"}, 404)
        try:
            record.action_cancel_draft()
            return _json(_case_dict(record, detail=True))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/morgue/patients/<int:patient_id>/admissions",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_patient_admissions(self, patient_id, limit=50, **kw):
        patient = request.env["res.partner"].sudo().browse(patient_id)
        if not patient.exists() or not patient.is_patient:
            return _json({"error": "patient not found"}, 404)

        try:
            limit = max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            limit = 50

        admissions = (
            request.env["saycare.admission.request"]
            .sudo()
            .search(
                [("patient_id", "=", patient.id)],
                order="admitted_at desc, create_date desc, id desc",
                limit=limit,
            )
        )

        return _json(
            {
                "patientId": patient.id,
                "admissions": [
                    {
                        "id": admission.id,
                        "status": admission.status or "",
                        "patientName": admission.patient_name or patient.name or "",
                        "patientMrn": admission.patient_mrn
                        or getattr(patient, "mrn", "")
                        or "",
                        "medicalFileNumber": admission.x_file_number
                        or getattr(patient, "x_file_number", "")
                        or "",
                        "entryPermitNo": admission.entry_permit_no
                        or getattr(patient, "x_entry_permit_no", "")
                        or "",
                        "nationalId": admission.national_id
                        or getattr(patient, "id_number", "")
                        or "",
                        "departmentId": admission.department_id.id
                        if admission.department_id
                        else None,
                        "departmentName": admission.department_id.display_name
                        if admission.department_id
                        else (admission.ward or ""),
                        "attendingDoctorName": admission.attending_doctor
                        or admission.doctor_name
                        or "",
                        "admissionDate": admission.admission_date.isoformat()
                        if admission.admission_date
                        else "",
                        "admittedAt": fields.Datetime.to_string(
                            admission.admitted_at
                        )
                        if admission.admitted_at
                        else "",
                        "inpatientBookingNumber": admission.inpatient_booking_number
                        or "",
                    }
                    for admission in admissions
                ],
            }
        )
    @http.route(
        "/api/v1/morgue/fridges",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_fridges(self, available_only="1", **kw):
        only_available = _bool_value(available_only)
        fridges = request.env["saycare.morgue.fridge"].sudo().search(
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

class MorgueOperationsController(http.Controller):
    @staticmethod
    def _stored_case_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_no or "",
            "deceasedName": record.deceased_name or "",
            "patientMrn": record.patient_mrn or "",
            "state": record.state or "",
            "fridgeId": record.fridge_id.id if record.fridge_id else None,
            "fridgeName": record.fridge_id.name if record.fridge_id else "",
            "fridgeCode": record.fridge_id.code if record.fridge_id else "",
            "drawerId": record.drawer_id.id if record.drawer_id else None,
            "drawerCode": record.drawer_id.code if record.drawer_id else "",
            "drawerName": record.drawer_id.name if record.drawer_id else "",
            "belongingsStatus": record.belongings_status or "",
        }

    @staticmethod
    def _movement_dict(record):
        return {
            "id": record.id,
            "caseId": record.case_id.id,
            "caseNo": record.case_id.case_no or "",
            "fromFridgeId": record.from_fridge_id.id,
            "fromFridgeName": record.from_fridge_id.name or "",
            "fromDrawerId": record.from_drawer_id.id,
            "fromDrawerCode": record.from_drawer_id.code or "",
            "toFridgeId": record.to_fridge_id.id,
            "toFridgeName": record.to_fridge_id.name or "",
            "toDrawerId": record.to_drawer_id.id,
            "toDrawerCode": record.to_drawer_id.code or "",
            "reason": record.reason or "",
            "movedByName": record.moved_by_id.name if record.moved_by_id else "",
            "movedAt": fields.Datetime.to_string(record.moved_at)
            if record.moved_at
            else "",
        }

    @staticmethod
    def _belonging_values(body):
        item_name = (body.get("itemName") or "").strip()
        if not item_name:
            raise ValidationError(_("اسم المتعلَّق مطلوب."))

        try:
            quantity = int(body.get("quantity") or 1)
        except (TypeError, ValueError):
            raise ValidationError(_("الكمية يجب أن تكون رقماً صحيحاً."))
        if quantity <= 0:
            raise ValidationError(_("الكمية يجب أن تكون أكبر من صفر."))

        return {
            "category": body.get("category") or "other",
            "item_name": item_name,
            "description": (body.get("description") or "").strip(),
            "quantity": quantity,
            "condition": (body.get("condition") or "").strip(),
            "sealed_container_no": (
                body.get("sealedContainerNo") or ""
            ).strip(),
            "storage_location": (body.get("storageLocation") or "").strip(),
            "notes": (body.get("notes") or "").strip(),
            "status": body.get("status") or "stored",
        }

    @http.route(
        "/api/v1/morgue/stored-cases",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def stored_cases(self, **kw):
        cases = request.env["saycare.morgue.case"].sudo().search(
            [("state", "=", "stored")],
            order="reception_datetime desc, id desc",
        )
        return _json(
            {"cases": [self._stored_case_dict(record) for record in cases]}
        )

    @http.route(
        "/api/v1/morgue/storage",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def storage(self, **kw):
        fridges = request.env["saycare.morgue.fridge"].sudo().search(
            [("active", "=", True)],
            order="code asc",
        )
        result = []
        for fridge in fridges:
            drawers = []
            for drawer in fridge.drawer_ids.filtered("active"):
                case = drawer.current_case_id
                drawers.append(
                    {
                        "id": drawer.id,
                        "code": drawer.code or "",
                        "name": drawer.name or "",
                        "occupied": bool(case),
                        "currentCase": self._stored_case_dict(case)
                        if case
                        else None,
                    }
                )
            result.append(
                {
                    "id": fridge.id,
                    "code": fridge.code or "",
                    "name": fridge.name or "",
                    "location": fridge.location or "",
                    "drawers": drawers,
                    "total": len(drawers),
                    "occupied": len(
                        [drawer for drawer in drawers if drawer["occupied"]]
                    ),
                    "available": len(
                        [drawer for drawer in drawers if not drawer["occupied"]]
                    ),
                }
            )
        return _json({"fridges": result})

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/movements",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def movements(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)
        rows = request.env["saycare.morgue.movement"].sudo().search(
            [("case_id", "=", case.id)],
            order="moved_at desc, id desc",
        )
        return _json(
            {"movements": [self._movement_dict(record) for record in rows]}
        )

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/transfer",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def transfer(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)

        body, error = _load_body()
        if error:
            return error

        try:
            movement = case.action_transfer_storage(
                body.get("destinationDrawerId"),
                body.get("reason"),
            )
            return _json(
                {
                    "case": self._stored_case_dict(case),
                    "movement": self._movement_dict(movement),
                }
            )
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/belongings",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_belongings(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)
        return _json(
            {
                "case": self._stored_case_dict(case),
                "belongings": [
                    _belonging_dict(record) for record in case.belonging_ids
                ],
            }
        )

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/belongings",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def create_belonging(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)
        if case.state not in ("draft", "stored"):
            return _json(
                {"error": "لا يمكن تعديل متعلقات هذه الحالة."},
                409,
            )

        body, error = _load_body()
        if error:
            return error

        try:
            values = self._belonging_values(body)
            values["case_id"] = case.id
            record = request.env["saycare.morgue.belonging"].sudo().create(
                values
            )
            if case.belongings_status != "recorded":
                case.write({"belongings_status": "recorded"})
            return _json(_belonging_dict(record), 201)
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/belongings/<int:belonging_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_belonging(self, belonging_id, **kw):
        record = (
            request.env["saycare.morgue.belonging"]
            .sudo()
            .browse(belonging_id)
        )
        if not record.exists():
            return _json({"error": "المتعلَّق غير موجود."}, 404)
        if record.case_id.state not in ("draft", "stored"):
            return _json(
                {"error": "لا يمكن تعديل متعلقات هذه الحالة."},
                409,
            )

        body, error = _load_body()
        if error:
            return error

        try:
            record.write(self._belonging_values(body))
            return _json(_belonging_dict(record))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/belongings/<int:belonging_id>",
        type="http",
        auth="user",
        methods=["DELETE"],
        csrf=False,
    )
    def delete_belonging(self, belonging_id, **kw):
        record = (
            request.env["saycare.morgue.belonging"]
            .sudo()
            .browse(belonging_id)
        )
        if not record.exists():
            return _json({"error": "المتعلَّق غير موجود."}, 404)
        case = record.case_id
        if case.state not in ("draft", "stored"):
            return _json(
                {"error": "لا يمكن تعديل متعلقات هذه الحالة."},
                409,
            )

        record.unlink()
        if not case.belonging_ids and case.belongings_status == "recorded":
            case.write({"belongings_status": "none"})
        return _json({"ok": True})


class MorgueAutopsyReleaseController(http.Controller):
    @staticmethod
    def _employee_dict(record):
        return {
            "id": record.id,
            "name": record.name or "",
            "jobTitle": getattr(record, "job_title", "") or "",
        }

    @staticmethod
    def _case_option_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_no or "",
            "deceasedName": record.deceased_name or "",
            "patientMrn": record.patient_mrn or "",
            "state": record.state or "",
            "fridgeId": record.fridge_id.id if record.fridge_id else None,
            "fridgeName": record.fridge_id.name if record.fridge_id else "",
            "fridgeCode": record.fridge_id.code if record.fridge_id else "",
            "drawerId": record.drawer_id.id if record.drawer_id else None,
            "drawerCode": record.drawer_id.code if record.drawer_id else "",
            "drawerName": record.drawer_id.name if record.drawer_id else "",
        }

    @staticmethod
    def _autopsy_dict(record):
        return {
            "id": record.id,
            "caseId": record.case_id.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "caseState": record.case_id.state or "",
            "status": record.status or "",
            "requestedAt": fields.Datetime.to_string(record.requested_at)
            if record.requested_at
            else "",
            "requestedById": record.requested_by_id.id
            if record.requested_by_id
            else None,
            "requestedByName": record.requested_by_id.name
            if record.requested_by_id
            else "",
            "assignedDoctorId": record.assigned_doctor_id.id
            if record.assigned_doctor_id
            else None,
            "assignedDoctorName": record.assigned_doctor_id.name
            if record.assigned_doctor_id
            else "",
            "reason": record.reason or "",
            "clinicalNotes": record.clinical_notes or "",
            "autopsyAt": fields.Datetime.to_string(record.autopsy_at)
            if record.autopsy_at
            else "",
            "findings": record.findings or "",
            "reportText": record.report_text or "",
            "completedByName": record.completed_by_id.name
            if record.completed_by_id
            else "",
            "completedAt": fields.Datetime.to_string(record.completed_at)
            if record.completed_at
            else "",
            "cancelReason": record.cancel_reason or "",
        }

    @staticmethod
    def _release_dict(record):
        return {
            "id": record.id,
            "caseId": record.case_id.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "receiverName": record.receiver_name or "",
            "receiverIdType": record.receiver_id_type or "",
            "receiverIdNumber": record.receiver_id_number or "",
            "relationToDeceased": record.relation_to_deceased or "",
            "permitReference": record.permit_reference or "",
            "notes": record.notes or "",
            "releasedByName": record.released_by_id.name
            if record.released_by_id
            else "",
            "releasedAt": fields.Datetime.to_string(record.released_at)
            if record.released_at
            else "",
            "fromFridgeName": record.from_fridge_id.name or "",
            "fromFridgeCode": record.from_fridge_id.code or "",
            "fromDrawerCode": record.from_drawer_id.code or "",
            "fromDrawerName": record.from_drawer_id.name or "",
        }

    @staticmethod
    def _parse_datetime(value):
        value = (value or "").strip()
        if not value:
            return False

        normalized = value.replace("T", " ")
        if len(normalized) == 16:
            normalized += ":00"
        try:
            return fields.Datetime.to_datetime(normalized)
        except Exception:
            raise ValidationError("صيغة التاريخ والوقت غير صحيحة.")

    @http.route(
        "/api/v1/morgue/employees",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def employees(self, **kw):
        employees = request.env["hr.employee"].sudo().search(
            [("active", "=", True)],
            order="name asc",
            limit=500,
        )
        return _json(
            {"employees": [self._employee_dict(record) for record in employees]}
        )

    @http.route(
        "/api/v1/morgue/autopsy-cases",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def autopsy_cases(self, **kw):
        cases = request.env["saycare.morgue.case"].sudo().search(
            [("state", "in", ["stored", "released"])],
            order="reception_datetime desc, id desc",
        )
        return _json(
            {"cases": [self._case_option_dict(record) for record in cases]}
        )

    @http.route(
        "/api/v1/morgue/autopsies",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_autopsies(self, case_id="", **kw):
        domain = []
        if case_id:
            try:
                domain.append(("case_id", "=", int(case_id)))
            except (TypeError, ValueError):
                return _json({"error": "معرف الحالة غير صحيح."}, 400)

        records = request.env["saycare.morgue.autopsy"].sudo().search(
            domain,
            order="requested_at desc, id desc",
        )
        return _json(
            {"autopsies": [self._autopsy_dict(record) for record in records]}
        )

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/autopsies",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def create_autopsy(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)
        if case.state not in ("stored", "released"):
            return _json(
                {"error": "لا يمكن إنشاء طلب تشريح لهذه الحالة."},
                409,
            )

        body, error = _load_body()
        if error:
            return error

        reason = (body.get("reason") or "").strip()
        if not reason:
            return _json({"error": "سبب التشريح مطلوب."}, 400)

        doctor_id = body.get("assignedDoctorId")
        if doctor_id:
            try:
                doctor_id = int(doctor_id)
            except (TypeError, ValueError):
                return _json({"error": "الطبيب المحدد غير صحيح."}, 400)
            doctor = request.env["hr.employee"].sudo().browse(doctor_id)
            if not doctor.exists():
                return _json({"error": "الطبيب المحدد غير موجود."}, 404)
        else:
            doctor_id = False

        try:
            record = request.env["saycare.morgue.autopsy"].sudo().create(
                {
                    "case_id": case.id,
                    "assigned_doctor_id": doctor_id,
                    "reason": reason,
                    "clinical_notes": (
                        body.get("clinicalNotes") or ""
                    ).strip(),
                }
            )
            return _json(self._autopsy_dict(record), 201)
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/autopsies/<int:autopsy_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_autopsy(self, autopsy_id, **kw):
        record = request.env["saycare.morgue.autopsy"].sudo().browse(autopsy_id)
        if not record.exists():
            return _json({"error": "طلب التشريح غير موجود."}, 404)
        if record.status != "requested":
            return _json(
                {"error": "يمكن تعديل طلب التشريح قبل بدء التنفيذ فقط."},
                409,
            )

        body, error = _load_body()
        if error:
            return error

        values = {}
        if "reason" in body:
            reason = (body.get("reason") or "").strip()
            if not reason:
                return _json({"error": "سبب التشريح مطلوب."}, 400)
            values["reason"] = reason
        if "clinicalNotes" in body:
            values["clinical_notes"] = (
                body.get("clinicalNotes") or ""
            ).strip()
        if "assignedDoctorId" in body:
            doctor_id = body.get("assignedDoctorId")
            if doctor_id:
                try:
                    doctor_id = int(doctor_id)
                except (TypeError, ValueError):
                    return _json({"error": "الطبيب المحدد غير صحيح."}, 400)
                doctor = request.env["hr.employee"].sudo().browse(doctor_id)
                if not doctor.exists():
                    return _json(
                        {"error": "الطبيب المحدد غير موجود."},
                        404,
                    )
                values["assigned_doctor_id"] = doctor.id
            else:
                values["assigned_doctor_id"] = False

        try:
            if values:
                record.write(values)
            return _json(self._autopsy_dict(record))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/autopsies/<int:autopsy_id>/start",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def start_autopsy(self, autopsy_id, **kw):
        record = request.env["saycare.morgue.autopsy"].sudo().browse(autopsy_id)
        if not record.exists():
            return _json({"error": "طلب التشريح غير موجود."}, 404)
        try:
            record.action_start()
            return _json(self._autopsy_dict(record))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/morgue/autopsies/<int:autopsy_id>/complete",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def complete_autopsy(self, autopsy_id, **kw):
        record = request.env["saycare.morgue.autopsy"].sudo().browse(autopsy_id)
        if not record.exists():
            return _json({"error": "طلب التشريح غير موجود."}, 404)

        body, error = _load_body()
        if error:
            return error

        try:
            record.action_complete(
                findings=body.get("findings"),
                report_text=body.get("reportText"),
                autopsy_at=self._parse_datetime(body.get("autopsyAt")),
            )
            return _json(self._autopsy_dict(record))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/morgue/autopsies/<int:autopsy_id>/cancel",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def cancel_autopsy(self, autopsy_id, **kw):
        record = request.env["saycare.morgue.autopsy"].sudo().browse(autopsy_id)
        if not record.exists():
            return _json({"error": "طلب التشريح غير موجود."}, 404)

        body, error = _load_body()
        if error:
            return error

        try:
            record.action_cancel(body.get("reason"))
            return _json(self._autopsy_dict(record))
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

    @http.route(
        "/api/v1/morgue/releases",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def list_releases(self, **kw):
        records = request.env["saycare.morgue.release"].sudo().search(
            [],
            order="released_at desc, id desc",
            limit=500,
        )
        return _json(
            {"releases": [self._release_dict(record) for record in records]}
        )

    @http.route(
        "/api/v1/morgue/cases/<int:case_id>/release",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def release_case(self, case_id, **kw):
        case = request.env["saycare.morgue.case"].sudo().browse(case_id)
        if not case.exists():
            return _json({"error": "الحالة غير موجودة."}, 404)

        body, error = _load_body()
        if error:
            return error

        try:
            release = case.action_release_body(
                receiver_name=body.get("receiverName"),
                receiver_id_type=body.get("receiverIdType") or "national_id",
                receiver_id_number=body.get("receiverIdNumber"),
                relation_to_deceased=body.get("relationToDeceased"),
                permit_reference=body.get("permitReference"),
                notes=body.get("notes"),
            )
            return _json(
                {
                    "release": self._release_dict(release),
                    "case": self._case_option_dict(case),
                }
            )
        except (ValidationError, UserError) as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 409)

class MorgueDashboardReportsSettingsController(http.Controller):
    @staticmethod
    def _datetime_text(value):
        return fields.Datetime.to_string(value) if value else ""

    @staticmethod
    def _or_domain(conditions):
        if not conditions:
            return []
        if len(conditions) == 1:
            return conditions
        return ["|"] * (len(conditions) - 1) + conditions

    @staticmethod
    def _date_domain(field_name, date_from="", date_to=""):
        domain = []
        try:
            if date_from:
                domain.append(
                    (
                        field_name,
                        ">=",
                        fields.Datetime.to_datetime(
                            f"{str(date_from).strip()} 00:00:00"
                        ),
                    )
                )
            if date_to:
                domain.append(
                    (
                        field_name,
                        "<=",
                        fields.Datetime.to_datetime(
                            f"{str(date_to).strip()} 23:59:59"
                        ),
                    )
                )
        except Exception:
            raise ValidationError("صيغة التاريخ غير صحيحة.")
        return domain

    @staticmethod
    def _body_bool(value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in ("1", "true", "yes", "on")

    @staticmethod
    def _case_report_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_no or "",
            "deceasedName": record.deceased_name or "",
            "patientMrn": record.patient_mrn or "",
            "sourceType": record.source_type or "",
            "state": record.state or "",
            "receptionDatetime": MorgueDashboardReportsSettingsController._datetime_text(
                record.reception_datetime
            ),
            "fridgeName": record.fridge_id.name if record.fridge_id else "",
            "fridgeCode": record.fridge_id.code if record.fridge_id else "",
            "drawerCode": record.drawer_id.code if record.drawer_id else "",
        }

    @staticmethod
    def _release_report_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "receiverName": record.receiver_name or "",
            "receiverIdNumber": record.receiver_id_number or "",
            "relationToDeceased": record.relation_to_deceased or "",
            "permitReference": record.permit_reference or "",
            "releasedAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.released_at
            ),
            "releasedByName": record.released_by_id.name
            if record.released_by_id
            else "",
            "fromFridgeName": record.from_fridge_id.name or "",
            "fromFridgeCode": record.from_fridge_id.code or "",
            "fromDrawerCode": record.from_drawer_id.code or "",
        }

    @staticmethod
    def _movement_report_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "fromFridgeName": record.from_fridge_id.name or "",
            "fromFridgeCode": record.from_fridge_id.code or "",
            "fromDrawerCode": record.from_drawer_id.code or "",
            "toFridgeName": record.to_fridge_id.name or "",
            "toFridgeCode": record.to_fridge_id.code or "",
            "toDrawerCode": record.to_drawer_id.code or "",
            "reason": record.reason or "",
            "movedAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.moved_at
            ),
            "movedByName": record.moved_by_id.name if record.moved_by_id else "",
        }

    @staticmethod
    def _autopsy_report_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "status": record.status or "",
            "reason": record.reason or "",
            "requestedAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.requested_at
            ),
            "assignedDoctorName": record.assigned_doctor_id.name
            if record.assigned_doctor_id
            else "",
            "autopsyAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.autopsy_at
            ),
            "completedAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.completed_at
            ),
        }

    @staticmethod
    def _belonging_report_dict(record):
        return {
            "id": record.id,
            "caseNo": record.case_id.case_no or "",
            "deceasedName": record.case_id.deceased_name or "",
            "category": record.category or "",
            "itemName": record.item_name or "",
            "quantity": record.quantity,
            "status": record.status or "",
            "sealedContainerNo": record.sealed_container_no or "",
            "storageLocation": record.storage_location or "",
            "receivedAt": MorgueDashboardReportsSettingsController._datetime_text(
                record.received_at
            ),
            "receivedByName": record.received_by_id.name
            if record.received_by_id
            else "",
        }

    @staticmethod
    def _drawer_settings_dict(record):
        case = record.current_case_id
        return {
            "id": record.id,
            "code": record.code or "",
            "name": record.name or "",
            "active": bool(record.active),
            "occupied": bool(case),
            "currentCase": {
                "id": case.id,
                "caseNo": case.case_no or "",
                "deceasedName": case.deceased_name or "",
            }
            if case
            else None,
        }

    @classmethod
    def _fridge_settings_dict(cls, fridge):
        drawers = sorted(fridge.drawer_ids, key=lambda row: row.code or "")
        serialized = [cls._drawer_settings_dict(row) for row in drawers]
        occupied = len([row for row in serialized if row["occupied"]])
        active_drawers = len([row for row in serialized if row["active"]])
        return {
            "id": fridge.id,
            "code": fridge.code or "",
            "name": fridge.name or "",
            "location": fridge.location or "",
            "active": bool(fridge.active),
            "drawers": serialized,
            "drawerCount": len(serialized),
            "activeDrawerCount": active_drawers,
            "occupiedDrawerCount": occupied,
            "hasOccupiedDrawers": occupied > 0,
        }

    @http.route(
        "/api/v1/morgue/dashboard",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def dashboard(self, **kw):
        Case = request.env["saycare.morgue.case"].sudo()
        Drawer = request.env["saycare.morgue.drawer"].sudo()
        Autopsy = request.env["saycare.morgue.autopsy"].sudo()
        Movement = request.env["saycare.morgue.movement"].sudo()
        Release = request.env["saycare.morgue.release"].sudo()

        case_counts = {
            state: Case.search_count([("state", "=", state)])
            for state in ("draft", "stored", "released", "cancelled")
        }

        total_drawers = Drawer.search_count([("active", "=", True)])
        occupied_drawers = Drawer.search_count(
            [
                ("active", "=", True),
                ("current_case_id", "!=", False),
            ]
        )
        available_drawers = max(total_drawers - occupied_drawers, 0)
        occupancy_percent = (
            round((occupied_drawers / total_drawers) * 100, 1)
            if total_drawers
            else 0.0
        )

        autopsy_counts = {
            state: Autopsy.search_count([("status", "=", state)])
            for state in ("requested", "in_progress", "completed", "cancelled")
        }

        recent_cases = Case.search(
            [],
            order="reception_datetime desc, id desc",
            limit=5,
        )
        recent_movements = Movement.search(
            [],
            order="moved_at desc, id desc",
            limit=5,
        )
        recent_releases = Release.search(
            [],
            order="released_at desc, id desc",
            limit=5,
        )

        return _json(
            {
                "cases": case_counts,
                "storage": {
                    "totalDrawers": total_drawers,
                    "occupiedDrawers": occupied_drawers,
                    "availableDrawers": available_drawers,
                    "occupancyPercent": occupancy_percent,
                },
                "autopsies": autopsy_counts,
                "recent": {
                    "receptions": [
                        self._case_report_dict(record) for record in recent_cases
                    ],
                    "movements": [
                        self._movement_report_dict(record)
                        for record in recent_movements
                    ],
                    "releases": [
                        self._release_report_dict(record)
                        for record in recent_releases
                    ],
                },
            }
        )

    @http.route(
        "/api/v1/morgue/reports",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def reports(
        self,
        report_type="cases",
        date_from="",
        date_to="",
        q="",
        status="",
        **kw,
    ):
        report_type = (report_type or "cases").strip().lower()
        q = (q or "").strip()
        status = (status or "").strip()

        specs = {
            "cases": {
                "model": "saycare.morgue.case",
                "date": "reception_datetime",
                "order": "reception_datetime desc, id desc",
                "serializer": self._case_report_dict,
            },
            "releases": {
                "model": "saycare.morgue.release",
                "date": "released_at",
                "order": "released_at desc, id desc",
                "serializer": self._release_report_dict,
            },
            "movements": {
                "model": "saycare.morgue.movement",
                "date": "moved_at",
                "order": "moved_at desc, id desc",
                "serializer": self._movement_report_dict,
            },
            "autopsies": {
                "model": "saycare.morgue.autopsy",
                "date": "requested_at",
                "order": "requested_at desc, id desc",
                "serializer": self._autopsy_report_dict,
            },
            "belongings": {
                "model": "saycare.morgue.belonging",
                "date": "received_at",
                "order": "received_at desc, id desc",
                "serializer": self._belonging_report_dict,
            },
        }

        spec = specs.get(report_type)
        if not spec:
            return _json({"error": "نوع التقرير غير صحيح."}, 400)

        try:
            domain = self._date_domain(
                spec["date"],
                date_from=date_from,
                date_to=date_to,
            )
        except ValidationError as exc:
            return _json({"error": str(exc)}, 400)

        if report_type == "cases":
            if status:
                domain.append(("state", "=", status))
            if q:
                domain += self._or_domain(
                    [
                        ("case_no", "ilike", q),
                        ("deceased_name", "ilike", q),
                        ("patient_mrn", "ilike", q),
                    ]
                )
        elif report_type == "releases":
            if q:
                domain += self._or_domain(
                    [
                        ("case_id.case_no", "ilike", q),
                        ("case_id.deceased_name", "ilike", q),
                        ("receiver_name", "ilike", q),
                        ("receiver_id_number", "ilike", q),
                        ("permit_reference", "ilike", q),
                    ]
                )
        elif report_type == "movements":
            if q:
                domain += self._or_domain(
                    [
                        ("case_id.case_no", "ilike", q),
                        ("case_id.deceased_name", "ilike", q),
                        ("reason", "ilike", q),
                        ("from_drawer_id.code", "ilike", q),
                        ("to_drawer_id.code", "ilike", q),
                    ]
                )
        elif report_type == "autopsies":
            if status:
                domain.append(("status", "=", status))
            if q:
                domain += self._or_domain(
                    [
                        ("case_id.case_no", "ilike", q),
                        ("case_id.deceased_name", "ilike", q),
                        ("reason", "ilike", q),
                        ("assigned_doctor_id.name", "ilike", q),
                    ]
                )
        elif report_type == "belongings":
            if status:
                domain.append(("status", "=", status))
            if q:
                domain += self._or_domain(
                    [
                        ("case_id.case_no", "ilike", q),
                        ("case_id.deceased_name", "ilike", q),
                        ("item_name", "ilike", q),
                        ("sealed_container_no", "ilike", q),
                        ("storage_location", "ilike", q),
                    ]
                )

        records = request.env[spec["model"]].sudo().search(
            domain,
            order=spec["order"],
            limit=1000,
        )

        return _json(
            {
                "reportType": report_type,
                "rows": [spec["serializer"](record) for record in records],
                "count": len(records),
            }
        )

    @http.route(
        "/api/v1/morgue/settings/fridges",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def settings_fridges(self, **kw):
        fridges = request.env["saycare.morgue.fridge"].sudo().with_context(
            active_test=False
        ).search([], order="code asc")

        return _json(
            {
                "fridges": [
                    self._fridge_settings_dict(fridge) for fridge in fridges
                ]
            }
        )

    @http.route(
        "/api/v1/morgue/settings/fridges",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def create_fridge(self, **kw):
        body, error = _load_body()
        if error:
            return error

        code = (body.get("code") or "").strip()
        name = (body.get("name") or "").strip()
        location = (body.get("location") or "").strip()

        if not code or not name:
            return _json({"error": "كود واسم الثلاجة مطلوبان."}, 400)

        try:
            fridge = request.env["saycare.morgue.fridge"].sudo().create(
                {
                    "code": code,
                    "name": name,
                    "location": location,
                    "active": True,
                }
            )
            return _json(self._fridge_settings_dict(fridge), 201)
        except Exception as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/settings/fridges/<int:fridge_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_fridge(self, fridge_id, **kw):
        fridge = request.env["saycare.morgue.fridge"].sudo().with_context(
            active_test=False
        ).browse(fridge_id)
        if not fridge.exists():
            return _json({"error": "الثلاجة غير موجودة."}, 404)

        body, error = _load_body()
        if error:
            return error

        values = {}
        if "code" in body:
            code = (body.get("code") or "").strip()
            if not code:
                return _json({"error": "كود الثلاجة مطلوب."}, 400)
            values["code"] = code
        if "name" in body:
            name = (body.get("name") or "").strip()
            if not name:
                return _json({"error": "اسم الثلاجة مطلوب."}, 400)
            values["name"] = name
        if "location" in body:
            values["location"] = (body.get("location") or "").strip()

        try:
            if values:
                fridge.write(values)
            return _json(self._fridge_settings_dict(fridge))
        except Exception as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/settings/fridges/<int:fridge_id>/toggle",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def toggle_fridge(self, fridge_id, **kw):
        fridge = request.env["saycare.morgue.fridge"].sudo().with_context(
            active_test=False
        ).browse(fridge_id)
        if not fridge.exists():
            return _json({"error": "الثلاجة غير موجودة."}, 404)

        body, error = _load_body()
        if error:
            return error

        active = self._body_bool(body.get("active"))

        if not active and fridge.drawer_ids.filtered("current_case_id"):
            return _json(
                {"error": "لا يمكن تعطيل ثلاجة تحتوي على درج مشغول."},
                409,
            )

        fridge.write({"active": active})
        return _json(self._fridge_settings_dict(fridge))

    @http.route(
        "/api/v1/morgue/settings/fridges/<int:fridge_id>/drawers",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def create_drawer(self, fridge_id, **kw):
        fridge = request.env["saycare.morgue.fridge"].sudo().with_context(
            active_test=False
        ).browse(fridge_id)
        if not fridge.exists():
            return _json({"error": "الثلاجة غير موجودة."}, 404)

        body, error = _load_body()
        if error:
            return error

        code = (body.get("code") or "").strip()
        name = (body.get("name") or "").strip()

        if not code:
            return _json({"error": "كود الدرج مطلوب."}, 400)

        try:
            drawer = request.env["saycare.morgue.drawer"].sudo().create(
                {
                    "fridge_id": fridge.id,
                    "code": code,
                    "name": name,
                    "active": True,
                }
            )
            return _json(self._drawer_settings_dict(drawer), 201)
        except Exception as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/settings/drawers/<int:drawer_id>",
        type="http",
        auth="user",
        methods=["PUT"],
        csrf=False,
    )
    def update_drawer(self, drawer_id, **kw):
        drawer = request.env["saycare.morgue.drawer"].sudo().with_context(
            active_test=False
        ).browse(drawer_id)
        if not drawer.exists():
            return _json({"error": "الدرج غير موجود."}, 404)

        body, error = _load_body()
        if error:
            return error

        values = {}
        if "code" in body:
            code = (body.get("code") or "").strip()
            if not code:
                return _json({"error": "كود الدرج مطلوب."}, 400)
            values["code"] = code
        if "name" in body:
            values["name"] = (body.get("name") or "").strip()

        try:
            if values:
                drawer.write(values)
            return _json(self._drawer_settings_dict(drawer))
        except Exception as exc:
            request.env.cr.rollback()
            return _json({"error": str(exc)}, 400)

    @http.route(
        "/api/v1/morgue/settings/drawers/<int:drawer_id>/toggle",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def toggle_drawer(self, drawer_id, **kw):
        drawer = request.env["saycare.morgue.drawer"].sudo().with_context(
            active_test=False
        ).browse(drawer_id)
        if not drawer.exists():
            return _json({"error": "الدرج غير موجود."}, 404)

        body, error = _load_body()
        if error:
            return error

        active = self._body_bool(body.get("active"))

        if not active and drawer.current_case_id:
            return _json(
                {"error": "لا يمكن تعطيل درج مشغول."},
                409,
            )

        if active and not drawer.fridge_id.active:
            return _json(
                {"error": "قم بتفعيل الثلاجة أولاً قبل تفعيل الدرج."},
                409,
            )

        drawer.write({"active": active})
        return _json(self._drawer_settings_dict(drawer))