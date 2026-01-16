{
    'name': 'Kal3iya Stock',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Pilot Stock Management Module based on Movement Ledger (Kal3iya)',
    'description': """
Stock Kal3iya
=============
This module provides a robust stock management system based on an immutable movement ledger.
- Independent from existing Kal3iya module.
- Movement-based stock core.
- No deletion of validated operations.
- Reversal moves for cancellations.
    """,
    'author': 'Soufiane-Food',
    'depends': ['base', 'web', 'mail', 'custom_employee'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/stock_kal3iya_root_menu.xml',
        'views/stock_kal3iya_move_views.xml',
        'views/stock_kal3iya_entry_views.xml',
        'views/stock_kal3iya_return_views.xml',
        'views/stock_kal3iya_exit_views.xml',
        'views/stock_kal3iya_stock_views.xml',
        'views/stock_kal3iya_master_data_views.xml',
        'views/stock_kal3iya_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}



