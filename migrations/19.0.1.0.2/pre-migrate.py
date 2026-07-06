# -*- coding: utf-8 -*-
"""Remove stale ir.model.fields metadata for fields dropped from code.

Each field below was replaced by a different field (not a plain rename), so
the leftover ir.model.fields row is still tracked as module data. Odoo's
end-of-upgrade cleanup (ir.model.data._process_end) tries to unlink it and
hits:
    "This column contains module data and cannot be removed!"
because the row's state is 'base' (defined by code) and that cleanup does not
run with the module-uninstall context set — a safety check meant for
interactive/UI deletions, not upgrades. Deleting the metadata (and dropping
the leftover column, if still present) directly via SQL sidesteps it.
"""

STALE_FIELDS = [
    # (model, field name, table)
    ('hospital.floor', 'department_id', 'hospital_floor'),  # replaced by department_ids (m2m)
    ('res.partner',    'blood_type',    'res_partner'),      # replaced by x_blood_type
]


def migrate(cr, version):
    # Generic sweep: any ir.model.fields.selection row whose field is no longer
    # of type 'selection' (changed to Char/etc. in code) is stale metadata that
    # crashes the same end-of-upgrade cleanup with
    # "'Char' object has no attribute 'ondelete'" — regardless of which field
    # it is, it can never be legitimate, so it's always safe to remove.
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection'
           AND res_id IN (
               SELECT s.id
                 FROM ir_model_fields_selection s
                 JOIN ir_model_fields f ON f.id = s.field_id
                WHERE f.ttype != 'selection'
           )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields_selection s
         USING ir_model_fields f
        WHERE f.id = s.field_id AND f.ttype != 'selection'
    """)

    for model, field_name, table in STALE_FIELDS:
        cr.execute(
            """
            DELETE FROM ir_model_data
             WHERE model = 'ir.model.fields'
               AND res_id IN (
                   SELECT id FROM ir_model_fields
                    WHERE model = %s AND name = %s
               )
            """,
            (model, field_name),
        )
        cr.execute(
            "DELETE FROM ir_model_fields WHERE model = %s AND name = %s",
            (model, field_name),
        )
        # Table may not exist yet on databases installing/upgrading fresh
        # (e.g. hospital_floor was never created on this DB) — skip in that case.
        cr.execute("SELECT to_regclass(%s)", (table,))
        if cr.fetchone()[0] is None:
            continue
        cr.execute(
            'ALTER TABLE "{}" DROP COLUMN IF EXISTS "{}"'.format(table, field_name)
        )
