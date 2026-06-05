# -*- coding: utf-8 -*-

def post_init_hook(env):
    _fix_journal_names(env)


def post_migrate_hook(env, *args, **kwargs):
    """Runs on every upgrade — strips يومية from journal names."""
    _fix_journal_names(env)


def uninstall_hook(env):
    pass


def _fix_journal_names(env):
    """
    For every financial_class journal:
    - Strip 'يومية ' prefix if present
    - Create the journal if none exists for that class yet
    """
    from .models.account_journal_ext import FINANCIAL_JOURNALS
    Journal = env['account.journal'].sudo()
    company  = env.company

    for fin_class, correct_name, code in FINANCIAL_JOURNALS:
        journals = Journal.search([
            ('financial_class', '=', fin_class),
            ('company_id', '=', company.id),
        ])
        if journals:
            # Rename any that still carry 'يومية'
            for j in journals:
                if 'يومية' in (j.name or ''):
                    try:
                        j.write({'name': correct_name})
                    except Exception:
                        pass
        else:
            # Create if completely missing
            effective_code = code
            if Journal.search([('code', '=', code), ('company_id', '=', company.id)], limit=1):
                effective_code = code + '2'
            try:
                Journal.create({
                    'name':            correct_name,
                    'code':            effective_code,
                    'type':            'sale',
                    'company_id':      company.id,
                    'financial_class': fin_class,
                })
            except Exception:
                pass
