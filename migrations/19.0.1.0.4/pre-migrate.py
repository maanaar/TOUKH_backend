# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Fixes 'column res_partner.x_entry_permit_no does not exist' on servers
    where this field was never successfully installed yet — most likely
    because a pre-existing manual field with the same name (added via
    Settings > Technical > Fields / Studio directly on that server) collided
    with it and blocked the upgrade. adopt_manual_field() is a no-op if
    there's no such collision, so it's safe to run unconditionally; it
    reuses the existing column (and its data) instead of deleting it.
    """
    from odoo.addons.saycare_odoo_19.hooks import adopt_manual_field
    adopt_manual_field(cr, 'res.partner', 'x_entry_permit_no')
