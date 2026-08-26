# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareNotification(models.Model):
    _name        = 'saycare.notification'
    _description = 'إشعار للمستخدم'
    _order       = 'create_date desc'

    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              index=True, ondelete='cascade')
    title   = fields.Char(string='العنوان', required=True)
    body    = fields.Char(string='التفاصيل')
    url     = fields.Char(string='الرابط')
    is_read = fields.Boolean(string='مقروء', default=False, index=True)
