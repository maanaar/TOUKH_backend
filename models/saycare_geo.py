# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareGovernorate(models.Model):
    _name        = 'saycare.governorate'
    _description = 'Egyptian Governorate'
    _order       = 'sequence, name'

    name        = fields.Char(string='المحافظة', required=True)
    region      = fields.Char(string='الإقليم')
    capital     = fields.Char(string='العاصمة / المركز الرئيسي')
    sequence    = fields.Integer(string='الترتيب', default=10)
    city_ids    = fields.One2many('saycare.city', 'governorate_id', string='المراكز / الأحياء')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'اسم المحافظة يجب أن يكون فريدًا.'),
    ]


class SaycareCity(models.Model):
    _name        = 'saycare.city'
    _description = 'Egyptian City / District (مركز أو حي)'
    _order       = 'governorate_id, name'

    name            = fields.Char(string='المركز / الحي', required=True)
    governorate_id  = fields.Many2one('saycare.governorate', string='المحافظة',
                                       required=True, ondelete='cascade', index=True)
