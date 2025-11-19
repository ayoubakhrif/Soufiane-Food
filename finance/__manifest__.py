{
    'name': 'Finance',
    'summary': 'Module pour la gestion finance',
    'author': 'Ayoub Akhrif',
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/data_cheque_view.xml',
        'views/data_views.xml',
        'views/benif_view.xml',
    ],
    'images': ['static/description/icon.svg'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
