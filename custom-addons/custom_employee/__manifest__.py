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
    'depends': ['base', 'mail', 'hr_org_chart'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/employee_views.xml',
        'views/department_views.xml',
        'views/job_position_views.xml',
        'views/notification_views.xml',
        'views/menus.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
