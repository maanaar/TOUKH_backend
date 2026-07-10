# -*- coding: utf-8 -*-
from odoo import models, fields


class HospitalAccommodationGradeType(models.Model):
    _name = "hospital.accommodation.grade.type"
    _description = "اسم درجة الإقامة"
    _order = "sequence, name"

    name = fields.Char("اسم الدرجة", required=True)
    sequence = fields.Integer("الترتيب", default=10)
    active = fields.Boolean("فعال", default=True)

    _sql_constraints = [
        ("grade_type_name_uniq", "unique(name)", "اسم الدرجة يجب أن يكون فريدًا."),
    ]
