{
    'name': 'Stock Casa (Hanane)',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Stock Management Module for Hanane',
    'description': """
Stock Casa
==========
This module provides a robust stock management system based on an immutable movement ledger.
    """,
    'author': 'Ayoub',
    'depends': ['base', 'web', 'mail', 'company_data', 'custom_employee', 'casa_stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/root_menu.xml',
        'wizard/casa_client_invoice_wizard_view.xml',
        'reports/report_client_invoice.xml',
        'reports/report_stock_product.xml',
        'views/casa_stock_return_views.xml',
        'views/stock_exit_views.xml',
        'views/casa_stock_order_views.xml',
        'views/stock_move_views.xml',
        'views/stock_entry_views.xml',
        'views/stock_stock_views.xml',
        'views/stock_client_views.xml',
        'views/master_data_views.xml',
        'views/stock_transfer_views.xml',
        'views/casa_stock_discount_views.xml',
        'views/other_sale_views.xml',
        'views/stock_perte_views.xml',
        'views/stock_difference_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}