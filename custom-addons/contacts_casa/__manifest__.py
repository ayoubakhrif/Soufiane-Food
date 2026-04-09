{
    'name': 'Contacts SF',
    'version': '1.0',
    'summary': 'Gestion des contacts SF',
    'category': 'Custom',
    'author': 'Casa',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/contacts_casa_views.xml',
    ],
    'installable': True,
    'application': True,
}
