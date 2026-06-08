# -*- coding: utf-8 -*-
from odoo import models, fields


class HospitalFloor(models.Model):
    _name = "hospital.floor"
    _description = "الدور"
    _order = "code"

    code = fields.Char("كود الدور", required=True, copy=False, index=True)
    name = fields.Char("اسم الدور", required=True)
    building = fields.Char("المبنى / الفرع")
    floor_no = fields.Char("رقم الدور")

    # القسم التابع له
    department_id = fields.Many2one(
        "hospital.inpatient.department",
        string="القسم التابع له",
        required=True,
        ondelete="restrict",
    )

    active = fields.Boolean("فعال", default=True)
    notes = fields.Text("ملاحظات")

