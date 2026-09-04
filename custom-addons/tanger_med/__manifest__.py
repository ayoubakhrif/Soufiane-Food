{
    'name': 'Tanger Med',
    'version': '1.0',
    'summary': 'Gestion de la phase opérationnelle Tanger Med',
    'description': """
        Module pour gérer la phase opérationnelle Tanger Med.
        - Suivi des dossiers sortis du port
        - Gestion du montant SUR+MAG
        - Traçabilité des dates et utilisateurs
    """,
    'category': 'Operations',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'logistique'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/tanger_med_views.xml',
        'views/tanger_med_destination_views.xml',
        'views/sutra_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
