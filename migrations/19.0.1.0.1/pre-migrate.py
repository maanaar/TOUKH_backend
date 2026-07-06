# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Remove the stale res.partner.x_payment_type field metadata.

    The field was dropped from partner_ext.py, but a leftover
    ir.model.fields row (registered as Char rather than Selection)
    was crashing the end-of-upgrade cleanup in ir.model.data._process_end,
    which expects the current field's `.ondelete` attribute while
    unlinking the old field's selection options.

    Raw SQL instead of field.unlink(): the ORM's unlink() routes through
    _prepare_update(), which blocks removing any code-defined field
    ("state != manual") outside of an actual module uninstall — a safety
    check meant for interactive/UI deletions, not this cleanup.
    """
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields'
           AND res_id IN (
               SELECT id FROM ir_model_fields
                WHERE model = 'res.partner' AND name = 'x_payment_type'
           )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'res.partner' AND name = 'x_payment_type'
    """)
    cr.execute("""SELECT to_regclass('res_partner')""")
    if cr.fetchone()[0] is not None:
        cr.execute('ALTER TABLE "res_partner" DROP COLUMN IF EXISTS "x_payment_type"')
