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
    'depends': ['base', 'achat', 'logistique', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/portnet_confirm_wizard_view.xml',
        'views/portnet_entry_view.xml',
        'views/portnet_virement_view.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
