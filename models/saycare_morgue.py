# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


_CASE_NO_ALLOWED_RE = re.compile(r"^[\w\u0600-\u06FF./\- ]+$", re.UNICODE)


class SaycareMorgueCase(models.Model):
    _name = "saycare.morgue.case"
    _description = "Morgue Reception Case"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reception_datetime desc, id desc"
    _rec_name = "case_no"

    case_no = fields.Char(
        string="Morgue Case Number",
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
        "saycare.morgue.fridge",
        string="Fridge",
        copy=False,
        tracking=True,
        ondelete="restrict",
    )
    drawer_id = fields.Many2one(
        "saycare.morgue.drawer",
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
        "saycare.morgue.belonging",
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
        "Morgue case number must be unique.",
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
            raise ValidationError(_("Morgue case number is required."))
        if not _CASE_NO_ALLOWED_RE.match(value):
            raise ValidationError(
                _("Morgue case number contains unsupported characters.")
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
        if (
            vals.get("state") == "released"
            and any(rec.state != "released" for rec in self)
            and not self.env.context.get("allow_morgue_release")
        ):
            raise UserError(
                _("Body release must use the morgue release workflow.")
            )

        if "case_no" in vals:
            vals["case_no"] = self._normalise_case_no(vals.get("case_no"))
            if any(rec.state != "draft" and vals["case_no"] != rec.case_no for rec in self):
                raise UserError(
                    _("The morgue case number cannot be changed after confirmation.")
                )

        protected_location_fields = {"fridge_id", "drawer_id"}
        if (
            protected_location_fields.intersection(vals)
            and any(rec.state != "draft" for rec in self)
            and not self.env.context.get("allow_morgue_transfer")
        ):
            raise UserError(
                _("Storage location changes must use the morgue transfer workflow.")
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
            "SELECT id FROM saycare_morgue_drawer WHERE id = %s FOR UPDATE",
            [drawer_id],
        )
        if not self.env.cr.fetchone():
            raise ValidationError(_("The selected drawer does not exist."))

        drawer = self.env["saycare.morgue.drawer"].sudo().browse(drawer_id)
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


class SaycareMorgueBelonging(models.Model):
    _name = "saycare.morgue.belonging"
    _description = "Morgue Personal Belonging"
    _order = "id asc"
    _rec_name = "item_name"

    case_id = fields.Many2one(
        "saycare.morgue.case",
        string="Morgue Case",
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


class SaycareMorgueFridge(models.Model):
    _name = "saycare.morgue.fridge"
    _description = "Morgue Fridge"
    _order = "code asc"
    _rec_name = "name"

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True)
    location = fields.Char(string="Location")
    active = fields.Boolean(string="Active", default=True, index=True)
    drawer_ids = fields.One2many(
        "saycare.morgue.drawer",
        "fridge_id",
        string="Drawers",
    )

    _fridge_code_uniq = models.Constraint(
        "unique(code)",
        "Fridge code must be unique.",
    )


class SaycareMorgueDrawer(models.Model):
    _name = "saycare.morgue.drawer"
    _description = "Morgue Drawer"
    _order = "fridge_id, code asc"
    _rec_name = "code"

    fridge_id = fields.Many2one(
        "saycare.morgue.fridge",
        string="Fridge",
        required=True,
        index=True,
        ondelete="cascade",
    )
    code = fields.Char(string="Drawer Code", required=True, index=True)
    name = fields.Char(string="Drawer Name")
    active = fields.Boolean(string="Active", default=True, index=True)
    current_case_id = fields.Many2one(
        "saycare.morgue.case",
        string="Current Morgue Case",
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
        "A morgue case cannot occupy more than one drawer.",
    )

class SaycareMorgueMovement(models.Model):
    _name = "saycare.morgue.movement"
    _description = "Morgue Body Movement"
    _order = "moved_at desc, id desc"

    case_id = fields.Many2one(
        "saycare.morgue.case",
        string="Morgue Case",
        required=True,
        index=True,
        ondelete="cascade",
    )
    from_fridge_id = fields.Many2one(
        "saycare.morgue.fridge",
        string="From Fridge",
        required=True,
        ondelete="restrict",
    )
    from_drawer_id = fields.Many2one(
        "saycare.morgue.drawer",
        string="From Drawer",
        required=True,
        ondelete="restrict",
    )
    to_fridge_id = fields.Many2one(
        "saycare.morgue.fridge",
        string="To Fridge",
        required=True,
        ondelete="restrict",
    )
    to_drawer_id = fields.Many2one(
        "saycare.morgue.drawer",
        string="To Drawer",
        required=True,
        ondelete="restrict",
    )
    reason = fields.Text(string="Transfer Reason", required=True)
    moved_by_id = fields.Many2one(
        "hr.employee",
        string="Moved By",
        ondelete="restrict",
    )
    moved_at = fields.Datetime(
        string="Moved At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )


class SaycareMorgueCaseTransfer(models.Model):
    _inherit = "saycare.morgue.case"

    movement_ids = fields.One2many(
        "saycare.morgue.movement",
        "case_id",
        string="Movement History",
    )

    def action_transfer_storage(self, destination_drawer_id, reason):
        self.ensure_one()

        if self.state != "stored":
            raise UserError(_("يمكن نقل الحالات المحفوظة فقط."))

        reason = (reason or "").strip()
        if not reason:
            raise ValidationError(_("سبب نقل الجثمان مطلوب."))

        if not self.drawer_id or not self.fridge_id:
            raise ValidationError(_("الحالة ليس لها موقع حفظ حالي صالح."))

        try:
            destination_drawer_id = int(destination_drawer_id)
        except (TypeError, ValueError):
            raise ValidationError(_("يجب اختيار درج وجهة صالح."))

        source_drawer = self.drawer_id
        if source_drawer.id == destination_drawer_id:
            raise ValidationError(_("يجب اختيار درج مختلف عن الدرج الحالي."))

        lock_ids = sorted({source_drawer.id, destination_drawer_id})
        self.env.cr.execute(
            """
            SELECT id
              FROM saycare_morgue_drawer
             WHERE id IN %s
             ORDER BY id
             FOR UPDATE
            """,
            [tuple(lock_ids)],
        )
        locked_ids = {row[0] for row in self.env.cr.fetchall()}
        if set(lock_ids) != locked_ids:
            raise ValidationError(_("أحد الأدراج المحددة غير موجود."))

        Drawer = self.env["saycare.morgue.drawer"].sudo()
        source_drawer = Drawer.browse(source_drawer.id)
        destination = Drawer.browse(destination_drawer_id)
        source_drawer.invalidate_recordset(
            ["active", "current_case_id", "fridge_id"]
        )
        destination.invalidate_recordset(
            ["active", "current_case_id", "fridge_id"]
        )

        if source_drawer.current_case_id != self:
            raise ValidationError(
                _("الدرج الحالي لم يعد مرتبطاً بهذه الحالة. قم بتحديث الصفحة.")
            )
        if not destination.active or not destination.fridge_id.active:
            raise ValidationError(_("الثلاجة أو الدرج الوجهة غير نشط."))
        if destination.current_case_id:
            raise ValidationError(_("الدرج الوجهة مشغول بالفعل."))

        from_fridge = self.fridge_id
        from_drawer = source_drawer
        employee = self._employee_for_current_user()

        source_drawer.write({"current_case_id": False})
        destination.write({"current_case_id": self.id})
        self.with_context(allow_morgue_transfer=True).write(
            {
                "fridge_id": destination.fridge_id.id,
                "drawer_id": destination.id,
            }
        )

        movement = self.env["saycare.morgue.movement"].sudo().create(
            {
                "case_id": self.id,
                "from_fridge_id": from_fridge.id,
                "from_drawer_id": from_drawer.id,
                "to_fridge_id": destination.fridge_id.id,
                "to_drawer_id": destination.id,
                "reason": reason,
                "moved_by_id": employee.id or False,
                "moved_at": fields.Datetime.now(),
            }
        )

        self.message_post(
            body=_("تم نقل الجثمان من %s / %s إلى %s / %s.")
            % (
                from_fridge.display_name,
                from_drawer.display_name,
                destination.fridge_id.display_name,
                destination.display_name,
            )
        )
        return movement


class SaycareMorgueAutopsy(models.Model):
    _name = "saycare.morgue.autopsy"
    _description = "Morgue Autopsy"
    _order = "requested_at desc, id desc"

    case_id = fields.Many2one(
        "saycare.morgue.case",
        string="Morgue Case",
        required=True,
        index=True,
        ondelete="cascade",
    )
    status = fields.Selection(
        [
            ("requested", "Requested"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="requested",
        required=True,
        index=True,
    )
    requested_at = fields.Datetime(
        string="Requested At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    requested_by_id = fields.Many2one(
        "hr.employee",
        string="Requested By",
        default=lambda self: self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        ),
        ondelete="restrict",
    )
    assigned_doctor_id = fields.Many2one(
        "hr.employee",
        string="Assigned Doctor / Pathologist",
        ondelete="restrict",
    )
    reason = fields.Text(string="Reason", required=True)
    clinical_notes = fields.Text(string="Clinical / Legal Notes")
    autopsy_at = fields.Datetime(string="Autopsy Date / Time")
    findings = fields.Text(string="Findings")
    report_text = fields.Text(string="Autopsy Report")
    completed_by_id = fields.Many2one(
        "hr.employee",
        string="Completed By",
        ondelete="restrict",
    )
    completed_at = fields.Datetime(string="Completed At", index=True)
    cancel_reason = fields.Text(string="Cancellation Reason")

    @api.constrains("reason")
    def _check_reason(self):
        for rec in self:
            if not (rec.reason or "").strip():
                raise ValidationError(_("Autopsy reason is required."))

    def _employee_for_current_user(self):
        return self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)],
            limit=1,
        )

    def action_start(self):
        self.ensure_one()
        if self.status != "requested":
            raise UserError(_("Only requested autopsies can be started."))
        self.write(
            {
                "status": "in_progress",
                "autopsy_at": self.autopsy_at or fields.Datetime.now(),
            }
        )
        return True

    def action_complete(self, findings="", report_text="", autopsy_at=False):
        self.ensure_one()
        if self.status not in ("requested", "in_progress"):
            raise UserError(
                _("Only requested or in-progress autopsies can be completed.")
            )

        findings = (findings or "").strip()
        report_text = (report_text or "").strip()
        if not findings and not report_text:
            raise ValidationError(
                _("Findings or autopsy report text is required.")
            )

        employee = self._employee_for_current_user()
        self.write(
            {
                "status": "completed",
                "findings": findings,
                "report_text": report_text,
                "autopsy_at": autopsy_at or self.autopsy_at or fields.Datetime.now(),
                "completed_by_id": employee.id or False,
                "completed_at": fields.Datetime.now(),
                "cancel_reason": False,
            }
        )
        return True

    def action_cancel(self, reason):
        self.ensure_one()
        if self.status not in ("requested", "in_progress"):
            raise UserError(
                _("Only requested or in-progress autopsies can be cancelled.")
            )

        reason = (reason or "").strip()
        if not reason:
            raise ValidationError(_("Cancellation reason is required."))

        self.write(
            {
                "status": "cancelled",
                "cancel_reason": reason,
            }
        )
        return True


class SaycareMorgueRelease(models.Model):
    _name = "saycare.morgue.release"
    _description = "Morgue Body Release"
    _order = "released_at desc, id desc"

    case_id = fields.Many2one(
        "saycare.morgue.case",
        string="Morgue Case",
        required=True,
        index=True,
        ondelete="restrict",
    )
    receiver_name = fields.Char(string="Receiver Name", required=True)
    receiver_id_type = fields.Selection(
        [
            ("national_id", "National ID"),
            ("passport", "Passport"),
            ("other", "Other"),
        ],
        string="Receiver ID Type",
        default="national_id",
        required=True,
    )
    receiver_id_number = fields.Char(
        string="Receiver ID Number",
        required=True,
        index=True,
    )
    relation_to_deceased = fields.Char(string="Relation to Deceased")
    permit_reference = fields.Char(
        string="Release Permit / Reference",
        required=True,
        index=True,
    )
    notes = fields.Text(string="Release Notes")
    released_by_id = fields.Many2one(
        "hr.employee",
        string="Released By",
        ondelete="restrict",
    )
    released_at = fields.Datetime(
        string="Released At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    from_fridge_id = fields.Many2one(
        "saycare.morgue.fridge",
        string="Release Fridge",
        required=True,
        ondelete="restrict",
    )
    from_drawer_id = fields.Many2one(
        "saycare.morgue.drawer",
        string="Release Drawer",
        required=True,
        ondelete="restrict",
    )

    _case_release_uniq = models.Constraint(
        "unique(case_id)",
        "A morgue case can only be released once.",
    )


class SaycareMorgueCaseRelease(models.Model):
    _inherit = "saycare.morgue.case"

    autopsy_ids = fields.One2many(
        "saycare.morgue.autopsy",
        "case_id",
        string="Autopsies",
    )
    release_ids = fields.One2many(
        "saycare.morgue.release",
        "case_id",
        string="Body Releases",
    )

    def action_release_body(
        self,
        receiver_name,
        receiver_id_type,
        receiver_id_number,
        relation_to_deceased,
        permit_reference,
        notes="",
    ):
        self.ensure_one()

        if self.state != "stored":
            raise UserError(_("Only stored cases can be released."))

        receiver_name = (receiver_name or "").strip()
        receiver_id_number = (receiver_id_number or "").strip()
        permit_reference = (permit_reference or "").strip()

        if not receiver_name:
            raise ValidationError(_("Receiver name is required."))
        if not receiver_id_number:
            raise ValidationError(_("Receiver ID number is required."))
        if not permit_reference:
            raise ValidationError(_("Release permit/reference is required."))
        if receiver_id_type not in ("national_id", "passport", "other"):
            receiver_id_type = "other"

        if not self.drawer_id or not self.fridge_id:
            raise ValidationError(_("The case has no valid current storage location."))

        if self.release_ids:
            raise UserError(_("This case has already been released."))

        drawer_id = self.drawer_id.id
        self.env.cr.execute(
            "SELECT id FROM saycare_morgue_drawer WHERE id = %s FOR UPDATE",
            [drawer_id],
        )
        if not self.env.cr.fetchone():
            raise ValidationError(_("The current drawer no longer exists."))

        drawer = self.env["saycare.morgue.drawer"].sudo().browse(drawer_id)
        drawer.invalidate_recordset(["current_case_id", "fridge_id", "active"])

        if drawer.current_case_id != self:
            raise ValidationError(
                _("The current drawer is no longer occupied by this case. Refresh and retry.")
            )

        from_fridge = self.fridge_id
        from_drawer = drawer
        employee = self._employee_for_current_user()

        release = self.env["saycare.morgue.release"].sudo().create(
            {
                "case_id": self.id,
                "receiver_name": receiver_name,
                "receiver_id_type": receiver_id_type,
                "receiver_id_number": receiver_id_number,
                "relation_to_deceased": (relation_to_deceased or "").strip(),
                "permit_reference": permit_reference,
                "notes": (notes or "").strip(),
                "released_by_id": employee.id or False,
                "released_at": fields.Datetime.now(),
                "from_fridge_id": from_fridge.id,
                "from_drawer_id": from_drawer.id,
            }
        )

        drawer.write({"current_case_id": False})
        self.with_context(allow_morgue_release=True).write({"state": "released"})

        self.message_post(
            body=_("Body released from %s / %s to %s.")
            % (
                from_fridge.display_name,
                from_drawer.display_name,
                receiver_name,
            )
        )

        return release