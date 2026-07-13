# -*- coding: utf-8 -*-

def post_init_hook(env):
    _fix_journal_names(env)


def post_migrate_hook(env, *args, **kwargs):
    """Runs on every upgrade — strips يومية from journal names and syncs clinic services."""
    _fix_journal_names(env)
    _sync_all_specialty_services(env)


def _sync_all_specialty_services(env):
    specialties = env['saycare.specialty'].sudo().search([('categ_id', '!=', False)])
    specialties._sync_services_from_categ()


def uninstall_hook(env):
    pass


def adopt_manual_field(cr, model, field_name):
    """Data-safe fix for a common deploy trap: a field this module defines in
    code collides with a pre-existing 'manual' ir.model.fields row on the
    target server — usually a field someone added by hand via Settings >
    Technical > Fields (or Studio) directly on that server, independent of
    this codebase. That collision is what crashes -u with a field-type/
    ondelete error (the same root cause as the x_payment_type crash fixed in
    migrations/19.0.1.0.1/pre-migrate.py).

    Deleting the field in the UI "fixes" it but destroys whatever data staff
    already typed into it. This instead only clears Odoo's *bookkeeping* row
    (ir.model.fields / ir.model.fields.selection + their ir.model.data
    entries) — never the underlying Postgres column. Odoo's own _auto_init
    checks the real column via information_schema, not ir_model_fields, so
    if the column already exists with a compatible type it's left exactly as
    is and simply gets re-registered as owned by this module; the data
    is preserved. Only genuinely incompatible type changes fall back to
    Odoo's own _auto_init column-rename safety net, same as any other field
    type change.

    Call this from a pre-migrate.py script (cr only, no env — same reason
    the x_payment_type fix uses raw SQL: the ORM's unlink() refuses to
    remove a code-defined field outside of a real module uninstall), once
    per (model, field_name) pair, BEFORE this module's own fields get
    reflected for the target version:

        from odoo.addons.saycare_odoo_19.hooks import adopt_manual_field

        def migrate(cr, version):
            adopt_manual_field(cr, 'res.partner', 'x_some_new_field')
    """
    cr.execute("""
        SELECT id, state FROM ir_model_fields
         WHERE model = %s AND name = %s
    """, (model, field_name))
    row = cr.fetchone()
    if not row:
        return  # field doesn't exist on this server yet — nothing to adopt
    field_id, state = row
    if state != 'manual':
        return  # already module-owned (or something else) — leave it alone

    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection'
           AND res_id IN (SELECT id FROM ir_model_fields_selection WHERE field_id = %s)
    """, (field_id,))
    cr.execute("DELETE FROM ir_model_fields_selection WHERE field_id = %s", (field_id,))
    cr.execute("""
        DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id = %s
    """, (field_id,))
    cr.execute("DELETE FROM ir_model_fields WHERE id = %s", (field_id,))


def _fix_journal_names(env):
    """
    For every financial_class journal:
    - Strip 'يومية ' prefix if present
    - Create the journal if none exists for that class yet
    - Ensure default_account_id is set (required for action_post to work)
    """
    from .models.account_journal_ext import FINANCIAL_JOURNALS
    Journal = env['account.journal'].sudo()
    company  = env.company

    income_account = env['account.account'].sudo().search([
        ('account_type', 'in', ['income', 'income_other']),
        ('company_id', '=', company.id),
    ], limit=1)

    for fin_class, correct_name, code in FINANCIAL_JOURNALS:
        journals = Journal.search([
            ('financial_class', '=', fin_class),
            ('company_id', '=', company.id),
        ])
        if journals:
            for j in journals:
                vals = {}
                if 'يومية' in (j.name or ''):
                    vals['name'] = correct_name
                if income_account and not j.default_account_id:
                    vals['default_account_id'] = income_account.id
                if vals:
                    try:
                        j.write(vals)
                    except Exception:
                        pass
        else:
            effective_code = code
            if Journal.search([('code', '=', code), ('company_id', '=', company.id)], limit=1):
                effective_code = code + '2'
            try:
                vals = {
                    'name':            correct_name,
                    'code':            effective_code,
                    'type':            'sale',
                    'company_id':      company.id,
                    'financial_class': fin_class,
                }
                if income_account:
                    vals['default_account_id'] = income_account.id
                Journal.create(vals)
            except Exception:
                pass
