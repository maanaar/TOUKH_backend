# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPickingSayCare(models.Model):
    _inherit = 'stock.picking'

    # طلبات صرف واستلام الأقسام: "من أرسل" و"من استلم" شخصان مختلفان غالباً
    # (موقع المصدر وموقع الوجهة قد يخصّان موظفين مختلفين) — لا يمكن استخدام
    # user_id الأصلي وحده لهذا الغرض لأنه حقل واحد يُكتب فوقه في كل مرحلة.
    # يُكتب كل حقل فقط عند حدوث فعله (controllers/main.py)، لا عند الإنشاء.
    sent_by_id     = fields.Many2one('res.users', string='أُرسل بواسطة', readonly=True)
    received_by_id = fields.Many2one('res.users', string='استُلم بواسطة', readonly=True)
