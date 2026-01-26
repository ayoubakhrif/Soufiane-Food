{
    'name': 'Suivi de Présence',
    'version': '1.1',
    'category': 'Human Resources',
    'summary': 'Full attendance tracking with Entry/Exit events',
    'description': """
        Attendance module tracking entry and exit as separate events.
        Includes Employee Management, Leaves, Configuration, and Monthly Salary calculation.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'custom_employee', 'mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/suivi_employee_view.xml',
        'views/suivi_presence_view.xml',
        'views/suivi_leave_view.xml',
        'views/suivi_salary_view.xml',
        'views/suivi_config_view.xml',
        'views/suivi_advance_view.xml',
        'views/suivi_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
