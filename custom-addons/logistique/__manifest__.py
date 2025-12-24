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
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/ste_view.xml',
        'views/supplier_view.xml',
        'views/article_view.xml',
        'views/shipping_view.xml',
        'views/container_view.xml',
        'views/logistics_entry_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
