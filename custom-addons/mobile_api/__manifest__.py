{
    'name': 'Mobile API',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'API for Mobile Warehouse Application',
    'description': """
        This module exposes a read-only API for the mobile warehouse application.
        It provides a daily stock snapshot based on FIFO rules.
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['stock_kal3iya'],
    'data': [
        'security/ir.model.access.csv',
        'views/mobile_stock_snapshot_views.xml',
    ],
    'installable': True,
    'application': False,
}
