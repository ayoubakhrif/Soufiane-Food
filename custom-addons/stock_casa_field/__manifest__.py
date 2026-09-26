{
    'name': 'Stock Casa Field',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Pilot Stock Management Module based on Movement Ledger (Casa)',
    'description': """
    Stock Casa
    =============
    This module provides a robust stock management system based on an immutable movement ledger.
        """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'web', 'mail', 'custom_employee'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/casa_field_stock_move_views.xml',
        'views/casa_field_stock_entry_views.xml',
        'views/casa_field_stock_return_views.xml',
        'views/casa_field_stock_exit_views.xml',
        'views/casa_field_stock_stock_views.xml',
        'views/casa_field_stock_master_data_views.xml',
        'views/casa_field_stock_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}


