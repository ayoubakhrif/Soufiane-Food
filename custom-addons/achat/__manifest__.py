{
    'name': 'Achat Management',
    'version': '1.0',
    'category': 'Purchase',
    'summary': 'Gestion des Achats et Dossiers Logistiques',
    'description': """
        Module Achat pour gérer la création des dossiers logistiques.
        - Création des BL
        - Gestion des Conteneurs
        - Vue dédiée pour les Acheteurs
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'logistique'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/purchase_entry_view.xml',
        'views/achat_enquete_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
