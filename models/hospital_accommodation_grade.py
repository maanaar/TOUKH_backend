# -*- coding: utf-8 -*-
from odoo import models, fields


class HospitalAccommodationGrade(models.Model):
    _name = "hospital.accommodation.grade"
    _description = "درجة الإقامة"
    _order = "code"

    code = fields.Char("كود الدرجة", required=True, copy=False, index=True)
    name = fields.Many2one(
        "hospital.accommodation.grade.type",
        string="اسم الدرجة",
        required=True,
    )
    accommodation_type = fields.Char("نوع الإقامة")
    price_per_day = fields.Float("سعر اليوم")
    # currency_id = fields.Many2one(
    #     "res.currency",
    #     string="العملة",
    #     default=lambda self: self.env.company.currency_id,
    # )
    # price_per_day = fields.Monetary(
    #     "سعر اليوم", currency_field="currency_id"
    # )

    include_nursing = fields.Boolean("تشمل تمريض؟")
    include_meals = fields.Boolean("تشمل وجبات؟")
    need_approval = fields.Boolean("تحتاج موافقة؟")

    active = fields.Boolean("فعال", default=True)

    _sql_constraints = [
        ("grade_code_uniq", "unique(code)", "كود الدرجة يجب أن يكون فريدًا."),
    ]