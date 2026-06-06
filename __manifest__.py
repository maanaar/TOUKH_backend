# -*- coding: utf-8 -*-
{
    'name': 'SayCare-odoo',
    'version': '19.0.1.0.0',
    'summary': 'HTTP REST Endpoints for Inventory, Purchase, Employee Requisition and Clinical HIS',
    'description': """
        Provides HTTP endpoints (returning Python objects as HTTP responses) for:
        - product.template
        - product.category
        - uom.uom
        - stock.picking + stock.move
        - stock.location
        - purchase.order
        - employee.purchase.requisition
        - res.partner (patient extension)
        - saycare.specialty
        - hr.employee (doctor/nurse extension)
        - saycare.medication.order
    """,
    'category': 'Technical',
    'author': 'Custom Dev',
    'depends': [
        'base',
        'product',
        'stock',
        'purchase',
        'uom',
        'hr',
        'account',
        'employee_purchase_requisition',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/product_template_inherit.xml',
        'views/partner_inherit.xml',
        'views/saycare_clinic_views.xml',
        'views/hr_employee_inherit.xml',
        'views/account_move_inherit.xml',
        'views/saycare_medicine_views.xml',
        'data/account_journals.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook':    'post_init_hook',
    'post_migrate_hook': 'post_migrate_hook',
}
