{
    'name': 'Planification des Achats',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Planification de l\'arrivage des conteneurs et gestion du budget hebdomadaire',
    'description': """
        Ce module permet de:
        - Configurer un budget maximum par semaine.
        - Saisir les dossiers d'achats avec les numéros de BL, factures, ETA et numéros de conteneurs.
        - Suivre les montants par semaine selon l'ETA des dossiers.
    """,
    'depends': ['base', 'purchase', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/planification_config_views.xml',
        'views/planification_dossier_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
