{
    'name': 'Business Apps Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Role-based Business Application Launcher',
    'description': """
        A custom dashboard that acts as a functional home menu.
        - Define Business Apps linked to Menus or Actions.
        - Role-based visibility using User Groups.
        - Kanban Launcher view.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'views/business_app_view.xml',
    ],
    'assets': {},
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
