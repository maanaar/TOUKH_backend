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
