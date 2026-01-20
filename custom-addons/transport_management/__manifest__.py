{
    'name': 'Transport Management',
    'version': '1.0',
    'summary': 'Manage transport trips and charges',
    'description': """
        Transport Management Module
        ===========================
        Track transport trips and analyze charges by driver, client, and types.
    """,
    'category': 'Logistics',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'mail', 'web', 'custom_employee'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/transport_trip_views.xml',
        'views/gazoil_refill_view.xml',
        'views/gazoil_sale_view.xml',
        'views/gazoil_stock_view.xml',
        'views/master_data_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
