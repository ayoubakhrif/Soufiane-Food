{
    'name': 'Achat Module',
    'version': '1.0',
    'summary': 'Module Achat partageant les données avec Logistique',
    'description': """
        Module Achat pour gérer les entrées logistiques du point de vue Achats.
        - Partage le modèle logistique.entry
        - Champs spécifiques Achat (Prix, Factures, etc.)
        - Gestion des droits d'accès
    """,
    'category': 'Purchase',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'logistique'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/achat_readonly_for_logistics.xml',
        'views/achat_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
