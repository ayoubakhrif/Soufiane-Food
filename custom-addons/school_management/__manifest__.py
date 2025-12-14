{
    'name': 'School Management',
    'version': '17.0.1.0.0',
    'category': 'Education',
    'summary': 'Comprehensive Private School Management System',
    'description': """
        A complete module to manage private school operations:
        - Student & Parent Management
        - Classes, Subjects, and Teachers
        - Grading and Academic Reports
        - Payments and Finance
    """,
    'author': 'Antigravity',
    'depends': ['base', 'mail'],
    'data': [
        'security/school_security.xml',
        'security/ir.model.access.csv',
        'views/school_menus.xml',
        'views/student_view.xml',
        'views/parent_view.xml',
        'views/class_view.xml',
        'views/subject_view.xml',
        'views/teacher_view.xml',
        'views/grade_view.xml',
        'views/payment_view.xml',
        'views/report_view.xml',
        'reports/report_actions.xml',
        'reports/student_bulletin_template.xml',
        'reports/payment_receipt_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
