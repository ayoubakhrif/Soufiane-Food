{
    'name': 'Suivi Mediouna',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Gestion de production et suivi journalier Mediouna',
    'description': """
        Ce module permet de:
        - Gérer la production journalière.
        - Suivre les records journaliers des présences (Mediouna et Agadir) avec calcul de salaire.
        - Générer des rapports journaliers (bénéfice = production - charges).
    """,
    'author': 'Antigravity',
    'depends': ['base', 'suivi_presence'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/production_views.xml',
        'views/daily_record_views.xml',
        'views/daily_report_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
