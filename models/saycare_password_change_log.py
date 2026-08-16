# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaycarePasswordChangeLog(models.Model):
    _name = 'saycare.password.change.log'
    _description = 'سجل تغييرات كلمات المرور'
    _order = 'create_date desc'
    _rec_name = 'user_id'

    # Never stores the password value itself, only the fact that a change
    # happened, who made it and when — create_date/create_uid already give
    # "when"/"by whom" for free, user_id is who was affected.
    user_id = fields.Many2one('res.users', string='المستخدم المتأثر', required=True, ondelete='cascade')
    login   = fields.Char(string='البريد / اسم الدخول', related='user_id.login', store=True, readonly=True)
    source  = fields.Selection([
        ('write',  'تعديل مباشر'),
        ('signup', 'تسجيل / دعوة'),
        ('reset',  'إعادة تعيين بريدياً'),
    ], string='المصدر', default='write')


class ResUsersPasswordTracking(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user, vals in zip(users, vals_list):
            if vals.get('password'):
                self.env['saycare.password.change.log'].sudo().create({
                    'user_id': user.id,
                    'source':  'signup',
                })
        return users

    def write(self, vals):
        password_changed = 'password' in vals and vals.get('password')
        result = super().write(vals)
        if password_changed:
            for user in self:
                self.env['saycare.password.change.log'].sudo().create({
                    'user_id': user.id,
                    'source':  'write',
                })
        return result
