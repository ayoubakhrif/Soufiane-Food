{
    'name': 'Dossier Lifecycle Monitoring',
    'version': '1.0',
    'summary': 'Read-only visualization of dossier lifecycles',
    'category': 'Operations',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'web', 'logistique', 'achat'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/monitoring_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
