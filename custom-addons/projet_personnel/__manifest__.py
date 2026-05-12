{
    'name': 'Projet Personnel',
    'version': '1.0',
    'summary': 'Manage personal item purchases, stock, and sales automatically.',
    'description': """
        Standalone module to track items:
        - Catalogue with colors and images
        - Purchase commands and automatic stock generation
        - Kanban view of stock items with pictures
        - Sale commands and profit calculation
    """,
    'author': 'Odoo',
    'website': '',
    'category': 'Custom',
    'depends': ['base', 'mail', 'suivi_personnel'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu_views.xml',
        'views/projet_item_views.xml',
        'views/projet_achat_views.xml',
        'views/projet_vente_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
