# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


_CASE_NO_ALLOWED_RE = re.compile(r"^[\w\u0600-\u06FF./\- ]+$", re.UNICODE)


class SaycareMortuaryCase(models.Model):
    _name = "saycare.mortuary.case"
    _description = "Mortuary Reception Case"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reception_datetime desc, id desc"
    _rec_name = "case_no"

    case_no = fields.Char(
        string="Mortuary Case Number",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("stored", "Stored"),
            ("released", "Released"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    source_type = fields.Selection(
        [
            ("internal", "Internal Hospital Death"),
            ("external", "Arrived from Outside"),
            ("unknown", "Unknown Identity"),
            ("referred", "Referred from Another Entity"),
        ],
        string="Case Source",
        default="internal",
        required=True,
        index=True,
        tracking=True,
    )

    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        domain=[("is_patient", "=", True)],
        index=True,
        ondelete="restrict",
    )
    admission_request_id = fields.Many2one(
        "saycare.admission.request",
        string="Admission Request",
        index=True,
        ondelete="restrict",
    )

    deceased_name = fields.Char(string="Deceased Name", tracking=True)
    patient_mrn = fields.Char(string="MRN", index=True)
    medical_file_number = fields.Char(string="Medical File Number", index=True)
    entry_permit_no = fields.Char(string="Entry Permit Number", index=True)
    id_type = fields.Selection(
        [("national_id", "National ID"), ("passport", "Passport")],
        string="ID Type",
        default="national_id",
    )
    id_number = fields.Char(string="ID Number", index=True)
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("unknown", "Unknown")],
        string="Gender",
    )
    date_of_birth = fields.Date(string="Date of Birth")
    age = fields.Integer(string="Age")
    nationality = fields.Char(string="Nationality")
    unknown_identity = fields.Boolean(string="Unknown Identity", tracking=True)
    identification_notes = fields.Text(string="Identification Notes / Distinguishing Marks")

    death_datetime = fields.Datetime(string="Death Date and Time", tracking=True)
    death_place = fields.Selection(
        [
            ("inside_hospital", "Inside Hospital"),
            ("outside_hospital", "Outside Hospital"),
            ("road_accident", "Road Accident"),
            ("home", "Home"),
            ("other", "Other"),
        ],
        string="Place of Death",
        tracking=True,
    )
    death_place_notes = fields.Char(string="Death Place Details")
    department_id = fields.Many2one(
        "hospital.inpatient.department",
        string="Hospital Department",
        ondelete="restrict",
    )
    attending_doctor_id = fields.Many2one(
        "hr.employee",
        string="Attending Doctor",
        domain=[("medical_role", "=", "doctor")],
        ondelete="restrict",
    )
    attending_doctor_name = fields.Char(string="Attending Doctor Name")
    cause_of_death = fields.Text(string="Cause of Death")
    death_type = fields.Selection(
        [
            ("natural", "Natural"),
            ("accident", "Accident"),
            ("criminal", "Criminal"),
            ("undetermined", "Undetermined"),
        ],
        string="Death Type",
        default="natural",
        tracking=True,
    )

    prosecution_case = fields.Boolean(string="Prosecution Case", tracking=True)
    prosecution_authority = fields.Char(string="Prosecution / Investigation Authority")
    police_report_no = fields.Char(string="Police Report Number", index=True)
    prosecution_case_no = fields.Char(string="Case / Investigation Number", index=True)
    prosecution_permit_datetime = fields.Datetime(string="Permit Date and Time")
    prosecution_notes = fields.Text(string="Prosecution Instructions / Restrictions")

    receiving_source = fields.Selection(
        [
            ("hospital_department", "Hospital Department"),
            ("emergency", "Emergency"),
            ("ambulance", "Ambulance"),
            ("police", "Police"),
            ("prosecution", "Prosecution"),
            ("other_hospital", "Other Hospital"),
            ("family", "Family"),
            ("other", "Other"),
        ],
        string="Received From",
    )
    referring_entity = fields.Char(string="Referring Entity")
    referring_reference = fields.Char(string="Referring Reference", index=True)
    delivered_by_name = fields.Char(string="Delivered By")
    delivered_by_role = fields.Char(string="Deliverer Role")
    delivered_by_id_number = fields.Char(string="Deliverer ID Number")
    delivered_by_phone = fields.Char(string="Deliverer Phone")
    ambulance_number = fields.Char(string="Ambulance / Vehicle Number")

    reception_datetime = fields.Datetime(
        string="Reception Date and Time",
        default=fields.Datetime.now,
        required=True,
        index=True,
        tracking=True,
    )
    received_by_id = fields.Many2one(
        "hr.employee",
        string="Received By",
        default=lambda self: self._default_employee(),
        ondelete="restrict",
    )
    fridge_id = fields.Many2one(
        "saycare.mortuary.fridge",
        string="Fridge",
        copy=False,
        tracking=True,
        ondelete="restrict",
    )
    drawer_id = fields.Many2one(
        "saycare.mortuary.drawer",
        string="Drawer",
        copy=False,
        tracking=True,
        ondelete="restrict",
    )

    belongings_status = fields.Selection(
        [
            ("not_reviewed", "Not Reviewed"),
            ("none", "No Belongings"),
            ("recorded", "Belongings Recorded"),
        ],
        string="Belongings Confirmation",
        default="not_reviewed",
        required=True,
        tracking=True,
    )
    belonging_ids = fields.One2many(
        "saycare.mortuary.belonging",
        "case_id",
        string="Personal Belongings",
        copy=True,
    )

    notes = fields.Text(string="Reception Notes")
    confirmed_by_id = fields.Many2one(
        "hr.employee",
        string="Confirmed By",
        copy=False,
        readonly=True,
        ondelete="restrict",
    )
    confirmed_at = fields.Datetime(
        string="Confirmed At",
        copy=False,
        readonly=True,
    )

    _case_no_uniq = models.Constraint(
        "unique(case_no)",
        "Mortuary case number must be unique.",
    )

    @api.model
    def _default_employee(self):
        return self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )

    @api.model
    def _normalise_case_no(self, value):
        value = " ".join((value or "").strip().split())
        if not value:
            raise ValidationError(_("Mortuary case number is required."))
        if not _CASE_NO_ALLOWED_RE.match(value):
            raise ValidationError(
                _("Mortuary case number contains unsupported characters.")
            )
        return value

    @api.model
    def _employee_for_current_user(self):
        return self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["case_no"] = self._normalise_case_no(vals.get("case_no"))
            self._apply_source_snapshots(vals)
            if vals.get("source_type") == "unknown":
                vals["unknown_identity"] = True
        return super().create(vals_list)

    def write(self, vals):
        if "case_no" in vals:
            vals["case_no"] = self._normalise_case_no(vals.get("case_no"))
            if any(rec.state != "draft" and vals["case_no"] != rec.case_no for rec in self):
                raise UserError(
                    _("The mortuary case number cannot be changed after confirmation.")
                )

        protected_location_fields = {"fridge_id", "drawer_id"}
        if protected_location_fields.intersection(vals) and any(
            rec.state != "draft" for rec in self
        ):
            raise UserError(
                _("Storage location changes must use the mortuary transfer workflow.")
            )

        self._apply_source_snapshots(vals)
        return super().write(vals)

    @api.model
    def _apply_source_snapshots(self, vals):
        if vals.get("patient_id"):
            patient = self.env["res.partner"].sudo().browse(vals["patient_id"])
            if patient.exists():
                vals.setdefault("deceased_name", patient.name or "")
                vals.setdefault("patient_mrn", getattr(patient, "mrn", "") or "")
                vals.setdefault(
                    "medical_file_number",
                    getattr(patient, "x_file_number", "") or "",
                )
                vals.setdefault(
                    "entry_permit_no",
                    getattr(patient, "x_entry_permit_no", "") or "",
                )
                vals.setdefault("id_type", getattr(patient, "id_type", "") or False)
                vals.setdefault("id_number", getattr(patient, "id_number", "") or "")
                vals.setdefault("gender", getattr(patient, "gender", "") or False)
                vals.setdefault("date_of_birth", getattr(patient, "dob", False))
                vals.setdefault(
                    "nationality",
                    patient.country_id.name if patient.country_id else "",
                )

        if vals.get("admission_request_id"):
            admission = (
                self.env["saycare.admission.request"]
                .sudo()
                .browse(vals["admission_request_id"])
            )
            if admission.exists():
                vals.setdefault("patient_id", admission.patient_id.id or False)
                vals.setdefault("deceased_name", admission.patient_name or "")
                vals.setdefault("patient_mrn", admission.patient_mrn or "")
                vals.setdefault(
                    "medical_file_number",
                    admission.x_file_number or "",
                )
                vals.setdefault("entry_permit_no", admission.entry_permit_no or "")
                vals.setdefault("id_number", admission.national_id or "")
                vals.setdefault(
                    "age",
                    int(admission.age) if str(admission.age or "").isdigit() else 0,
                )
                if admission.gender in ("male", "female", "unknown"):
                    vals.setdefault("gender", admission.gender)
                vals.setdefault(
                    "department_id",
                    admission.department_id.id or False,
                )
                vals.setdefault(
                    "attending_doctor_name",
                    admission.attending_doctor or admission.doctor_name or "",
                )

    @api.constrains("age")
    def _check_age(self):
        for rec in self:
            if rec.age < 0 or rec.age > 130:
                raise ValidationError(_("Age must be between 0 and 130."))

    @api.constrains("id_number", "id_type")
    def _check_identity_number(self):
        for rec in self:
            if (
                rec.id_type == "national_id"
                and rec.id_number
                and (not rec.id_number.isdigit() or len(rec.id_number) != 14)
            ):
                raise ValidationError(
                    _("National ID must contain exactly 14 digits.")
                )

    @api.constrains("death_datetime", "reception_datetime")
    def _check_reception_after_death(self):
        for rec in self:
            if (
                rec.death_datetime
                and rec.reception_datetime
                and rec.reception_datetime < rec.death_datetime
            ):
                raise ValidationError(
                    _("Reception date and time cannot be before death date and time.")
                )

    @api.constrains(
        "state",
        "fridge_id",
        "drawer_id",
        "belongings_status",
        "belonging_ids",
        "source_type",
        "patient_id",
        "deceased_name",
        "unknown_identity",
    )
    def _check_confirmed_case(self):
        for rec in self:
            if rec.state != "stored":
                continue
            if not rec.fridge_id or not rec.drawer_id:
                raise ValidationError(
                    _("A fridge and drawer are required before confirmation.")
                )
            if rec.drawer_id.fridge_id != rec.fridge_id:
                raise ValidationError(
                    _("The selected drawer does not belong to the selected fridge.")
                )
            if rec.source_type == "internal" and not rec.patient_id:
                raise ValidationError(
                    _("An internal hospital death must be linked to a patient.")
                )
            if not rec.unknown_identity and not (rec.deceased_name or "").strip():
                raise ValidationError(_("Deceased name is required."))
            if rec.belongings_status == "not_reviewed":
                raise ValidationError(
                    _("Confirm whether personal belongings were received.")
                )
            if rec.belongings_status == "recorded" and not rec.belonging_ids:
                raise ValidationError(
                    _("At least one personal belonging must be recorded.")
                )

    def action_confirm_storage(self, drawer_id):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft cases can be confirmed."))

        try:
            drawer_id = int(drawer_id)
        except (TypeError, ValueError):
            raise ValidationError(_("A valid drawer is required."))

        self.env.cr.execute(
            "SELECT id FROM saycare_mortuary_drawer WHERE id = %s FOR UPDATE",
            [drawer_id],
        )
        if not self.env.cr.fetchone():
            raise ValidationError(_("The selected drawer does not exist."))

        drawer = self.env["saycare.mortuary.drawer"].sudo().browse(drawer_id)
        drawer.invalidate_recordset(["active", "current_case_id", "fridge_id"])

        if not drawer.active or not drawer.fridge_id.active:
            raise ValidationError(_("The selected fridge or drawer is inactive."))
        if drawer.current_case_id and drawer.current_case_id != self:
            raise ValidationError(_("The selected drawer is already occupied."))

        employee = self._employee_for_current_user()
        self.write(
            {
                "fridge_id": drawer.fridge_id.id,
                "drawer_id": drawer.id,
                "state": "stored",
                "confirmed_by_id": employee.id or False,
                "confirmed_at": fields.Datetime.now(),
            }
        )
        drawer.write({"current_case_id": self.id})
        self.message_post(
            body=_("Reception confirmed and body assigned to drawer %s.")
            % drawer.display_name
        )
        return True

    def action_cancel_draft(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft cases can be cancelled."))
        self.write({"state": "cancelled"})
        return True


class SaycareMortuaryBelonging(models.Model):
    _name = "saycare.mortuary.belonging"
    _description = "Mortuary Personal Belonging"
    _order = "id asc"
    _rec_name = "item_name"

    case_id = fields.Many2one(
        "saycare.mortuary.case",
        string="Mortuary Case",
        required=True,
        index=True,
        ondelete="cascade",
    )
    category = fields.Selection(
        [
            ("documents", "Personal Documents"),
            ("cash", "Cash"),
            ("jewellery", "Jewellery"),
            ("device", "Phone / Device"),
            ("keys", "Keys"),
            ("clothes", "Clothes"),
            ("medicine", "Medicine"),
            ("other", "Other"),
        ],
        string="Category",
        default="other",
        required=True,
    )
    item_name = fields.Char(string="Item Name", required=True)
    description = fields.Text(string="Description")
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    condition = fields.Char(string="Condition at Reception")
    sealed_container_no = fields.Char(string="Sealed Bag / Envelope Number", index=True)
    storage_location = fields.Char(string="Storage Location")
    notes = fields.Text(string="Notes")
    status = fields.Selection(
        [
            ("stored", "Stored"),
            ("held", "Held"),
            ("released", "Released"),
        ],
        string="Status",
        default="stored",
        required=True,
        index=True,
    )
    received_by_id = fields.Many2one(
        "hr.employee",
        string="Received By",
        default=lambda self: self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        ),
        ondelete="restrict",
    )
    received_at = fields.Datetime(
        string="Received At",
        default=fields.Datetime.now,
        required=True,
    )

    @api.constrains("quantity")
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Belonging quantity must be greater than zero."))


class SaycareMortuaryFridge(models.Model):
    _name = "saycare.mortuary.fridge"
    _description = "Mortuary Fridge"
    _order = "code asc"
    _rec_name = "name"

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True)
    location = fields.Char(string="Location")
    active = fields.Boolean(string="Active", default=True, index=True)
    drawer_ids = fields.One2many(
        "saycare.mortuary.drawer",
        "fridge_id",
        string="Drawers",
    )

    _fridge_code_uniq = models.Constraint(
        "unique(code)",
        "Fridge code must be unique.",
    )


class SaycareMortuaryDrawer(models.Model):
    _name = "saycare.mortuary.drawer"
    _description = "Mortuary Drawer"
    _order = "fridge_id, code asc"
    _rec_name = "code"

    fridge_id = fields.Many2one(
        "saycare.mortuary.fridge",
        string="Fridge",
        required=True,
        index=True,
        ondelete="cascade",
    )
    code = fields.Char(string="Drawer Code", required=True, index=True)
    name = fields.Char(string="Drawer Name")
    active = fields.Boolean(string="Active", default=True, index=True)
    current_case_id = fields.Many2one(
        "saycare.mortuary.case",
        string="Current Mortuary Case",
        copy=False,
        index=True,
        ondelete="restrict",
    )

    _drawer_code_per_fridge_uniq = models.Constraint(
        "unique(fridge_id, code)",
        "Drawer code must be unique inside the fridge.",
    )
    _drawer_current_case_uniq = models.Constraint(
        "unique(current_case_id)",
        "A mortuary case cannot occupy more than one drawer.",
    )
