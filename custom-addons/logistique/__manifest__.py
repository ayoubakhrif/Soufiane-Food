{
    'name': 'Logistique',
    'version': '1.0',
    'summary': 'Gestion des entrées logistiques et des conteneurs',
    'description': """
        Module pour gérer les dossiers logistiques et le suivi des conteneurs.
        - Entrées logistiques
        - Gestion des conteneurs
        - Données de référence (Sociétés, Fournisseurs, Articles, Compagnies maritimes)
    """,
    'category': 'Operations',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/ste_view.xml',
        'views/supplier_view.xml',
        'views/article_view.xml',
        'views/shipping_view.xml',
        'views/container_view.xml',
        'views/logistics_entry_view.xml',
        'views/dossier_view.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
