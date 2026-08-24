# -*- coding: utf-8 -*-
from odoo import models, fields


class SaycareTriageAssessment(models.Model):
    _name        = 'saycare.triage.assessment'
    _description = 'مرفقات طبية - ملاحظات التمريض بالطوارئ'
    _order       = 'create_date desc'
    _rec_name    = 'visit_id'

    visit_id = fields.Many2one('saycare.visit', string='الزيارة', required=True,
                               ondelete='cascade', index=True)

    # ── بيانات الاستقبال ─────────────────────────────────────────────────────
    received_by_nurse   = fields.Char(string='الممرضة المستقبلة')
    doctor_name          = fields.Char(string='اسم الطبيب')
    doctor_arrival_time = fields.Char(string='وقت وصول الطبيب')

    # ── 1. ملاحظات الوصول ────────────────────────────────────────────────────
    arrival_accompaniment = fields.Selection([
        ('alone',       'وحيدا'),
        ('accompanied', 'مصحوبا'),
    ], string='حالة الوصول')
    arrival_method = fields.Selection([
        ('walking',    'مشيا'),
        ('ambulance',  'سيارة الإسعاف'),
        ('wheelchair', 'كرسي متحرك'),
        ('other',      'أخرى'),
    ], string='طريقة الوصول')
    call_time_1 = fields.Char(string='وقت الاستدعاء الأول')
    call_time_2 = fields.Char(string='وقت الاستدعاء الثاني')
    call_time_3 = fields.Char(string='وقت الاستدعاء الثالث')

    # ── 2. الشكوى المرضية ────────────────────────────────────────────────────
    complaint_classification = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ], string='تصنيف الحالة')

    # ── 3. الفحص ─────────────────────────────────────────────────────────────
    exam_weight       = fields.Char(string='الوزن')
    exam_bp             = fields.Char(string='الضغط (mmHg)')
    exam_temp           = fields.Char(string='الحرارة (°C)')
    exam_pulse         = fields.Char(string='النبض (دقيقة)')
    exam_rr             = fields.Char(string='التنفس (دقيقة)')
    exam_blood_sugar   = fields.Char(string='السكر بالدم (mg/dl)')
    exam_color = fields.Selection([
        ('normal', 'طبيعي'),
        ('yellow', 'مصفر'),
        ('pale',   'شاحب'),
        ('blue',   'مزرق'),
    ], string='اللون')
    exam_consciousness = fields.Selection([
        ('alert',        'واعي'),
        ('confused',     'مضطرب'),
        ('drowsy',       'ناعس'),
        ('unconscious',  'غير واعي'),
    ], string='درجة الوعي')

    # ── 4. حركة سير المريض ───────────────────────────────────────────────────
    disposition_time = fields.Char(string='الوقت')
    admitted_to = fields.Selection([
        ('unit', 'وحدة'),
        ('icu',  'رعاية جراحة (ICU)'),
        ('ccu',  'رعاية القلب (CCU)'),
        ('or',   'عمليات (OR)'),
    ], string='دخول إلى')
    discharged_to = fields.Selection([
        ('home',           'المنزل'),
        ('other_hospital', 'مستشفى أخرى'),
        ('death',          'وفاة'),
    ], string='خروج إلى')

    # ── 5. الحالة عند الخروج من الطوارئ ──────────────────────────────────────
    leaving_consciousness = fields.Selection([
        ('alert',        'واعي'),
        ('confused',     'مضطرب'),
        ('drowsy',       'ناعس'),
        ('unconscious',  'غير واعي'),
    ], string='درجة الوعي عند الخروج')
    leaving_bp     = fields.Char(string='الضغط عند الخروج (BP)')
    leaving_pulse = fields.Char(string='النبض عند الخروج (Pulse)')
    leaving_rr     = fields.Char(string='معدل التنفس عند الخروج (RR)')
    leaving_temp   = fields.Char(string='الحرارة عند الخروج (Temp)')
    leaving_spo2   = fields.Char(string='تشبع الأكسجين عند الخروج (Spo2 %)')
    leaving_color = fields.Selection([
        ('normal', 'طبيعي'),
        ('yellow', 'مصفر'),
        ('pale',   'شاحب'),
        ('blue',   'مزرق'),
    ], string='اللون عند الخروج')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('visit_uniq', 'unique(visit_id)', 'يوجد سجل مرفقات طبية لهذه الزيارة بالفعل.'),
    ]
