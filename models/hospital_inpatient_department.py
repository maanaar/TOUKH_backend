# -*- coding: utf-8 -*-
from odoo import models, fields


class HospitalInpatientDepartment(models.Model):
    _name = "hospital.inpatient.department"
    _description = "القسم الداخلي"
    _rec_name = "name_ar"
    _order = "code, name_ar"

    code = fields.Char("كود القسم الداخلي", required=True, copy=False, index=True)
    name_ar = fields.Char("اسم القسم الداخلي (عربي)", required=True)
    name_en = fields.Char("اسم القسم الداخلي (إنجليزي)")

    main_specialty = fields.Selection(
        selection=[
            ("internal", "باطنة"),
            ("surgery", "جراحة"),
            ("pediatrics", "أطفال"),
            ("gynecology", "نساء"),
            ("icu", "عناية"),
        ],
        string="التخصص الرئيسي",
        required=True,
    )
    ward_type = fields.Selection(
        selection=[
            ("male", "رجالي"),
            ("female", "حريمي"),
            ("children", "أطفال"),
            ("mixed", "مختلط"),
        ],
        string="النوع",
        required=True,
    )

    floor_count = fields.Integer("عدد الأدوار", compute="_compute_counts")
    bed_count = fields.Integer("عدد السراير", compute="_compute_counts")

    manager_id = fields.Many2one("hr.employee", string="المسؤول")
    head_nurse_id = fields.Many2one("hr.employee", string="التمريض المسؤول")

    active = fields.Boolean("فعال", default=True)
    notes = fields.Text("ملاحظات")

    _sql_constraints = [
        ("dept_code_uniq", "unique(code)", "كود القسم الداخلي يجب أن يكون فريدًا."),
    ]

    def _compute_counts(self):
        for rec in self:
            rec.floor_count = self.env["hospital.floor"].search_count(
                [("department_ids", "=", rec.id)]
            )
            rec.bed_count = self.env["hospital.bed"].search_count(
                [("department_id", "=", rec.id)]
            )