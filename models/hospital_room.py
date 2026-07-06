# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HospitalRoom(models.Model):
    _name = "hospital.room"
    _description = "الغرفة"
    _rec_name = "room_no"
    _order = "code"

    code = fields.Char("كود الغرفة", required=True, copy=False, index=True)
    room_no = fields.Char("رقم الغرفة", required=True)

    # الدور (الأب المباشر)
    floor_id = fields.Many2one(
        "hospital.floor",
        string="الدور",
        required=True,
        ondelete="restrict",
    )
    department_id = fields.Many2one(
        "hospital.inpatient.department",
        string="القسم",
        compute="_compute_department_id",
        store=True,
        readonly=False,
    )

    @api.depends("floor_id", "floor_id.department_ids")
    def _compute_department_id(self):
        for rec in self:
            rec.department_id = rec.floor_id.department_ids[:1]

    room_type = fields.Selection(
        selection=[
            ("normal", "عادية"),
            ("isolation", "عزل"),
            ("icu", "ICU"),
            ("operation", "عمليات"),
            ("emergency", "طوارئ"),
        ],
        string="نوع الغرفة",
        required=True,
    )
    allowed_gender = fields.Selection(
        selection=[
            ("male", "رجال"),
            ("female", "سيدات"),
            ("children", "أطفال"),
            ("all", "الكل"),
        ],
        string="الجنس المسموح",
        required=True,
        default="all",
    )

    capacity = fields.Integer("السعة (عدد السراير)")
    bed_count = fields.Integer("عدد السراير الفعلي", compute="_compute_bed_count")

    @api.depends()
    def _compute_bed_count(self):
        Bed = self.env["hospital.bed"]
        for rec in self:
            rec.bed_count = Bed.search_count([("room_id", "=", rec.id)])

    room_status = fields.Selection(
        selection=[
            ("available", "متاحة"),
            ("maintenance", "صيانة"),
            ("closed", "مغلقة"),
        ],
        string="الحالة",
        default="available",
        required=True,
    )

    active = fields.Boolean("فعال", default=True)


