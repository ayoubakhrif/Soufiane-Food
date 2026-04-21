{
    'name': 'Charges Casa',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Gestion des charges (Transport, Salaires, Autres)',
    'description': """
        Module pour la gestion des charges pour Casa.
    """,
    'author': 'Gestia',
    'depends': ['base', 'mail', 'casa_stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/charges_casa_views.xml',
    ],
    'installable': True,
    'application': True,
}
