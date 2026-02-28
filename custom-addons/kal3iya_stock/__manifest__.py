{
    'name': 'Kal3iya (Rami)',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Pilot Stock Management Module based on Movement Ledger (Kal3iya)',
    'description': """
    Stock Kal3iya
    =============
    This module provides a robust stock management system based on an immutable movement ledger.
        """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'web', 'mail', 'custom_employee'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/kal3iya_stock_move_views.xml',
        'views/kal3iya_stock_entry_views.xml',
        'views/kal3iya_stock_return_views.xml',
        'views/kal3iya_stock_exit_views.xml',
        'views/kal3iya_stock_stock_views.xml',
        'views/kal3iya_stock_master_data_views.xml',
        'views/kal3iya_stock_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
