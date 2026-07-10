# -*- coding: utf-8 -*-
"""hospital.accommodation.grade.name: Selection -> Many2one.

Rename the old varchar 'name' column out of the way before _auto_init runs,
so the ORM creates a fresh integer FK column for the many2one instead of
trying to alter the existing varchar column in place. post-migrate.py backfills
the new column from the renamed one and drops it.

Also drop the now-stale ir.model.fields.selection rows for this field, same
issue described in 19.0.1.0.2/pre-migrate.py (crashes end-of-upgrade cleanup
otherwise), but scoped to this specific field so it doesn't depend on ttype
already being reflected at this point in the upgrade.
"""


def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection'
           AND res_id IN (
               SELECT s.id
                 FROM ir_model_fields_selection s
                 JOIN ir_model_fields f ON f.id = s.field_id
                WHERE f.model = 'hospital.accommodation.grade' AND f.name = 'name'
           )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields_selection s
         USING ir_model_fields f
        WHERE f.id = s.field_id
          AND f.model = 'hospital.accommodation.grade' AND f.name = 'name'
    """)

    cr.execute("SELECT to_regclass('hospital_accommodation_grade')")
    if cr.fetchone()[0] is None:
        return

    cr.execute("""
        SELECT data_type FROM information_schema.columns
         WHERE table_name = 'hospital_accommodation_grade' AND column_name = 'name'
    """)
    row = cr.fetchone()
    if row and row[0] != 'integer':
        cr.execute(
            'ALTER TABLE "hospital_accommodation_grade" RENAME COLUMN "name" TO "name_old_selection"'
        )
