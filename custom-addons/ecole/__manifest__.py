{
    'name': 'Ecole',
    'version': '17.0.1.0.0',
    'category': 'Education',
    'summary': 'Basic School Management',
    'description': """
        Module Ecole pour la gestion scolaire.
    """,
    'author': 'Antigravity',
    'depends': ['base', 'mail',],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/ecole_menus.xml',
        'views/hide_apps_view.xml',
        'views/student_view.xml',
        'views/parent_view.xml',
        'views/school_class_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
