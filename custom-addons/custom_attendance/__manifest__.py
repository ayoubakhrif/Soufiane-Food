{
    'name': 'Présence et salaire',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manual Attendance and Monthly Salary Calculation',
    'description': """
        Independent module for managing employee attendance and salaries.
        - Custom Employee Model
        - Manual Daily Attendance with Lateness/Overtime logic
        - Monthly Salary Calculation
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'mail'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/employee_view.xml',
        'views/attendance_view.xml',
        'views/configuration_view.xml',
        'views/monthly_salary_view.xml',
        'views/leave_view.xml',
        'views/attendance_menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
