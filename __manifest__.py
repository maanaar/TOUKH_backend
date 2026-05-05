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
        'employee_purchase_requisition',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
