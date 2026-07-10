# -*- coding: utf-8 -*-
"""Backfill hospital.accommodation.grade.name (now Many2one) from the old
selection column renamed aside in pre-migrate.py, then drop it.
"""
from odoo import api, SUPERUSER_ID

OLD_KEY_TO_XMLID = {
    'economy': 'saycare_odoo_19.grade_type_economy',
    'normal':  'saycare_odoo_19.grade_type_normal',
    'private': 'saycare_odoo_19.grade_type_private',
    'vip':     'saycare_odoo_19.grade_type_vip',
    'icu':     'saycare_odoo_19.grade_type_icu',
}


def migrate(cr, version):
    cr.execute("SELECT to_regclass('hospital_accommodation_grade')")
    if cr.fetchone()[0] is None:
        return
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'hospital_accommodation_grade' AND column_name = 'name_old_selection'
    """)
    if not cr.fetchone():
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute('SELECT id, name_old_selection FROM hospital_accommodation_grade')
    for rec_id, old_key in cr.fetchall():
        xmlid = OLD_KEY_TO_XMLID.get(old_key)
        if not xmlid:
            continue
        type_rec = env.ref(xmlid, raise_if_not_found=False)
        if type_rec:
            cr.execute(
                'UPDATE hospital_accommodation_grade SET name = %s WHERE id = %s',
                (type_rec.id, rec_id),
            )

    cr.execute('ALTER TABLE hospital_accommodation_grade DROP COLUMN IF EXISTS name_old_selection')
