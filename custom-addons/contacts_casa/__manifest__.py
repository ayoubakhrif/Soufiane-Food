{
    'name': 'Contacts Casa',
    'version': '1.0',
    'summary': 'Gestion des contacts personnalisés',
    'category': 'Custom',
    'author': 'Casa',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/contacts_casa_views.xml',
    ],
    'installable': True,
    'application': True,
}
