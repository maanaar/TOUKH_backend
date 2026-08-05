# -*- coding: utf-8 -*-
{
    'name': 'SayCare-odoo',
    'version': '19.0.1.0.8',
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
        'mail',
        'medical_insurance',
        'employee_purchase_requisition',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/department_stock_sequences.xml',
        'data/main_warehouse_receipt_sequences.xml',
        'data/sequences.xml',
        'views/government_expense_views.xml',
        'views/product_template_inherit.xml',
        'views/partner_inherit.xml',
        'views/saycare_clinic_views.xml',
        'views/saycare_patient_views.xml',
        'views/hr_employee_inherit.xml',
        'views/account_move_inherit.xml',
        'views/saycare_medicine_views.xml',
        'views/hospital_department_views.xml',
        'views/hospital_floor_views.xml',
        'views/hospital_room_views.xml',
        'views/hospital_accommodation_grade_type_views.xml',
        'data/hospital_accommodation_grade_type_data.xml',
        'views/hospital_accommodation_grade_views.xml',
        'views/hospital_bed_views.xml',
        "views/hospital_menus.xml",
        'data/account_journals.xml',
        'data/default_services.xml',
        'data/saycare.governorate.csv',
        'data/saycare.city.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook':    'post_init_hook',
    'post_migrate_hook': 'post_migrate_hook',
}
