{
    'name': 'Gestion de Projet',
    'version': '17.0.1.0.0',
    'summary': 'Module de gestion de projets et de tâches associées',
    'author': 'Your Company',
    'category': 'Project Management',
    'license': 'LGPL-3',
    'depends': ['base', 'custom_employee'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/project_report.xml',
        'views/project_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
