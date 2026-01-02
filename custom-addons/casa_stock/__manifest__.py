{
    'name': 'Stock Casa',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Pilot Stock Management Module based on Movement Ledger',
    'description': """
Stock Casa
==========
This module provides a robust stock management system based on an immutable movement ledger.
- Independent from Kal3iya.
- Movement-based stock core.
- No deletion of validated operations.
- Reversal moves for cancellations.
    """,
    'author': 'Soufiane-Food',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/stock_stock_views.xml',
        'views/stock_entry_views.xml',
        'views/stock_exit_views.xml',
        'views/stock_move_views.xml',
        'views/master_data_views.xml',
        'views/commercial_views.xml',
        'views/client_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
