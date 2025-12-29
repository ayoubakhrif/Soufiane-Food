{
    'name': 'Custom Employee',
    'version': '1.0',
    'summary': 'Centralized Custom Employee Management',
    'description': """
        Independent lightweight employee module for custom applications.
        Does not depend on standard HR module.
    """,
    'category': 'Custom',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
