{
    'name': 'Contrôle TVA',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Gestion des déclarations de décaissement et fournisseurs',
    'description': """
        Module pour gérer les déclarations de décaissement, les fournisseurs
        associés, le calcul automatique de la TVA et les contrôles sur les dates
        et l'unicité des numéros de facture.
    """,
    'author': 'Antigravity',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/designation_views.xml',
        'views/fournisseur_views.xml',
        'views/declaration_views.xml',
        'views/decaissement_views.xml',
        'views/encaissement_views.xml',
        'views/menus_views.xml',
    ],
    'installable': True,
    'application': True,
}
