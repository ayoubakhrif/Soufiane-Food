{
    'name': 'Portnet',
    'version': '1.0',
    'category': 'Logistique',
    'summary': 'Gestion des entrées Portnet',
    'description': """
        Module Portnet pour gérer les dossiers Portnet.
        - Saisie des articles, origines, fournisseurs
        - Gestion des Incoterms (CFR, FOB, Emirate)
        - Liaison avec les sociétés et factures
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'achat', 'logistique'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/portnet_entry_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
