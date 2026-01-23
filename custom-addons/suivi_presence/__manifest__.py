{
    'name': 'Suivi de Présence',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Simple attendance tracking',
    'description': """
        Simplified attendance module tracking entry and exit as separate events.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'custom_attendance'], # Depends on custom_attendance for custom.employee
    'data': [
        'security/ir.model.access.csv',
        'views/suivi_presence_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
