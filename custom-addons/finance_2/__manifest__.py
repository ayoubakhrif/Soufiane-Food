{
    'name': 'finance_2',
    'version': '15.0.1.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Gestion simplifiée des chèques physiques',
    'description': """
        Nouveau module de gestion de finance simplifié.
        - Chèques physiques centralisés
        - Suivi logistique
        - Bot d'assignation
    """,
    'author': 'Gestia',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/personne_views.xml',
        'views/cheque_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
