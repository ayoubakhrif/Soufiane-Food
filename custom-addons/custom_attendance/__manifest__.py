{
    'name': 'Custom Attendance & Salary',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manual Attendance and Monthly Salary Calculation',
    'description': """
        Independent module for managing employee attendance and salaries.
        - Custom Employee Model
        - Manual Daily Attendance with Lateness/Overtime logic
        - Monthly Salary Calculation
    """,
    'author': 'Antigravity',
    'depends': ['base'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/attendance_menus.xml',
        'views/employee_view.xml',
        'views/attendance_view.xml',
        'views/configuration_view.xml',
        'views/monthly_salary_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
