{
    'name': 'Audit',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Module d\'audit des factures avec IA',
    'description': """
        Ce module permet d'auditer les factures en extrayant automatiquement
        les informations (Fournisseur, N° facture, Date) à partir d'un PDF via l'IA.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'mail'],
    'data': [
        'security/audit_security.xml',
        'security/ir.model.access.csv',
        'views/audit_invoice_views.xml',
        'views/audit_menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
