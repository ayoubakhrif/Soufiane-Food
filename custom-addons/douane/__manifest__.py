{
    'name': 'Douane / Transit',
    'version': '1.0',
    'summary': 'Suivi Douane et Transit des Dossiers Logistiques',
    'description': """
        Module d'extension pour le suivi Douane et Transit.
        - Suivi des DUM, Droits de douane, TVA
        - Gestion des documents douaniers
    """,
    'category': 'Operations',
    'author': 'Ayoub Akhrif',
    'depends': ['logistique'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/douane_entry_view.xml',
        'views/dossier_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
