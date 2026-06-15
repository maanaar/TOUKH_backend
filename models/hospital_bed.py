# -*- coding: utf-8 -*-
from odoo import models, fields


class HospitalBed(models.Model):
    _name = "hospital.bed"
    _description = "السرير"
    _rec_name = "bed_no"
    _order = "code"

    code = fields.Char("كود السرير", required=True, copy=False, index=True)
    bed_no = fields.Char("رقم السرير", required=True)

    # الغرفة (الأب المباشر)
    room_id = fields.Many2one(
        "hospital.room",
        string="الغرفة",
        required=True,
        ondelete="restrict",
    )
    # الدور والقسم يتم اختيارهما يدويًا
    floor_id = fields.Many2one(
        "hospital.floor",
        string="الدور",
    )
    department_id = fields.Many2one(
        "hospital.inpatient.department",
        string="القسم",
    )

    # الإقامة ترتبط بالسرير
    grade_id = fields.Many2one(
        "hospital.accommodation.grade",
        string="الدرجة / الإقامة",
    )

    bed_status = fields.Selection(
        selection=[
            ("available", "متاح"),
            ("occupied", "مشغول"),
            ("cleaning", "تنظيف"),
            ("maintenance", "صيانة"),
            ("reserved", "محجوز"),
        ],
        string="حالة السرير",
        default="available",
        required=True,
    )
    allowed_gender = fields.Selection(
        selection=[
            ("male", "رجال"),
            ("female", "سيدات"),
            ("children", "أطفال"),
            ("all", "الكل"),
        ],
        string="مخصص لـ",
        default="all",
    )

    current_patient_id = fields.Many2one("res.partner", string="مريض حاليًا")
    last_occupancy_date = fields.Datetime("تاريخ آخر إشغال")

    active = fields.Boolean("فعال", default=True)

